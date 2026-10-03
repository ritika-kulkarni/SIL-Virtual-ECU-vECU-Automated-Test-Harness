"""Fault injector for frame drop, bus-off, and J1939 TP retransmission."""

from __future__ import annotations

import random
import time

from sil_harness.bus.canif import CanIf
from sil_harness.bus.com import Com
from sil_harness.bus.interfaces import BusBackend, CanFrame
from sil_harness.bus.j1939_tp import J1939Transport
from sil_harness.bus.pdur import PduR
from sil_harness.core.config import Expectations, FaultSpec
from sil_harness.core.errors import FaultInjectionError
from sil_harness.core.logging import get_logger
from sil_harness.fault.models import FaultResult

log = get_logger(__name__)


class FaultInjector:
    def __init__(self, bus: BusBackend, seed: int = 42) -> None:
        self.bus = bus
        self.rng = random.Random(seed)
        self.canif = CanIf(bus)
        self.pdur = PduR(self.canif)
        self.com = Com(self.pdur)

    def apply(self, fault: FaultSpec, expectations: Expectations) -> FaultResult:
        if fault.type == "frame_drop":
            return self._frame_drop(fault, expectations)
        if fault.type == "bus_off":
            return self._bus_off(fault, expectations)
        if fault.type == "j1939_tp_retransmit":
            return self._j1939_tp(fault, expectations)
        raise FaultInjectionError(f"Unknown fault type: {fault.type}")

    def _frame_drop(self, fault: FaultSpec, expectations: Expectations) -> FaultResult:
        can_ids = set(fault.can_ids)
        window_end = time.monotonic() + (fault.window_ms / 1000.0)
        sent = 0
        dropped = 0

        def predicate(frame: CanFrame) -> bool:
            nonlocal dropped
            if time.monotonic() > window_end:
                return False
            if can_ids and frame.can_id not in can_ids:
                return False
            if self.rng.random() < fault.drop_rate:
                dropped += 1
                return True
            return False

        if hasattr(self.bus, "set_drop_predicate"):
            self.bus.set_drop_predicate(predicate)
        else:
            raise FaultInjectionError("Backend does not support frame-drop predicates")

        # Generate traffic across targeted IDs
        for i in range(20):
            can_id = fault.can_ids[i % len(fault.can_ids)] if fault.can_ids else 0x18FF1200
            ok = self.canif.transmit(can_id, bytes([i & 0xFF]) * 8)
            sent += 1
            if not ok:
                # already counted via predicate / bus-off
                pass
            # drain
            self.canif.receive(timeout_ms=5)

        if hasattr(self.bus, "set_drop_predicate"):
            self.bus.set_drop_predicate(None)

        received = self.bus.stats().rx_count
        drop_ratio = dropped / sent if sent else 0.0
        recovered = not self.bus.is_bus_off()
        passed = (
            received >= expectations.min_frames_received
            and drop_ratio <= expectations.max_drop_ratio
            and (recovered if expectations.require_recovery else True)
        )
        log.info(
            "frame_drop sent=%s dropped=%s received=%s ratio=%.2f passed=%s",
            sent,
            dropped,
            received,
            drop_ratio,
            passed,
        )
        return FaultResult(
            fault_type="frame_drop",
            applied=True,
            details={"sent": sent, "dropped": dropped, "received": received},
            metrics={
                "drop_ratio": drop_ratio,
                "passed": passed,
                "recovered": recovered,
            },
        )

    def _bus_off(self, fault: FaultSpec, expectations: Expectations) -> FaultResult:
        for _ in range(fault.error_frames_before_bus_off):
            self.bus.inject_error_frame()
            if self.bus.is_bus_off():
                break
        if not self.bus.is_bus_off():
            self.bus.force_bus_off()

        bus_off_seen = self.bus.is_bus_off()
        start = time.monotonic()
        # Recovery after window
        time.sleep(min(0.01, fault.recovery_window_ms / 1000.0))
        self.bus.recover()
        recovery_ms = (time.monotonic() - start) * 1000.0
        recovered = not self.bus.is_bus_off()

        passed = True
        if expectations.require_bus_off and not bus_off_seen:
            passed = False
        if expectations.require_recovery and not recovered:
            passed = False
        if expectations.max_recovery_ms and recovery_ms > expectations.max_recovery_ms:
            passed = False

        return FaultResult(
            fault_type="bus_off",
            applied=True,
            details={"bus_off_seen": bus_off_seen, "recovery_ms": recovery_ms},
            metrics={"passed": passed, "recovered": recovered, "recovery_ms": recovery_ms},
        )

    def _j1939_tp(self, fault: FaultSpec, expectations: Expectations) -> FaultResult:
        tp = J1939Transport(
            self.canif,
            max_retries=fault.max_tp_retries,
        )
        tp.force_control_drops(fault.drop_control_frames)
        payload = bytes([i % 256 for i in range(fault.payload_bytes)])
        session = tp.send_message(payload)

        passed = True
        if expectations.require_delivery and not session.delivered:
            passed = False
        if expectations.require_retransmit and session.retries < 1:
            passed = False
        if expectations.max_retries_observed and session.retries > expectations.max_retries_observed:
            passed = False

        return FaultResult(
            fault_type="j1939_tp_retransmit",
            applied=True,
            details={
                "retries": session.retries,
                "delivered": session.delivered,
                "abort": session.abort,
                "notes": session.notes,
            },
            metrics={
                "passed": passed,
                "retries": session.retries,
                "bytes_delivered": session.bytes_delivered,
            },
        )
