"""In-process Python CAN bus simulator."""

from __future__ import annotations

import time
from collections import deque

from sil_harness.bus.interfaces import BusStats, CanFrame
from sil_harness.core.errors import BusBackendError
from sil_harness.core.logging import get_logger

log = get_logger(__name__)


class PythonBusSimulator:
    """In-process virtual CAN bus for SIL (no hardware, no CANoe)."""

    name = "python"

    def __init__(self, channel: int = 0, bitrate: int = 500_000) -> None:
        self.channel = channel
        self.bitrate = bitrate
        self._queue: deque[CanFrame] = deque()
        self._attached = False
        self._bus_off = False
        self._error_counter = 0
        self._stats = BusStats()
        self._drop_predicate = None  # optional callable(CanFrame) -> bool

    def set_drop_predicate(self, predicate) -> None:
        self._drop_predicate = predicate

    def attach(self) -> None:
        self._attached = True
        self._bus_off = False
        self._error_counter = 0
        log.info("Python bus attached channel=%s bitrate=%s", self.channel, self.bitrate)

    def detach(self) -> None:
        self._attached = False
        self._queue.clear()
        log.info("Python bus detached")

    def _ensure_attached(self) -> None:
        if not self._attached:
            raise BusBackendError("Bus not attached")

    def send(self, frame: CanFrame) -> bool:
        self._ensure_attached()
        if self._bus_off:
            self._stats.dropped_count += 1
            return False
        if self._drop_predicate and self._drop_predicate(frame):
            self._stats.dropped_count += 1
            return False
        stamped = CanFrame(
            can_id=frame.can_id,
            data=bytes(frame.data),
            is_extended=frame.is_extended,
            timestamp_ms=time.monotonic() * 1000.0,
        )
        self._queue.append(stamped)
        self._stats.tx_count += 1
        return True

    def receive(self, timeout_ms: float = 100.0) -> CanFrame | None:
        self._ensure_attached()
        if self._bus_off:
            return None
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        while True:
            if self._queue:
                frame = self._queue.popleft()
                self._stats.rx_count += 1
                return frame
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.001)

    def inject_error_frame(self) -> None:
        self._ensure_attached()
        self._error_counter += 1
        if self._error_counter >= 32:
            self.force_bus_off()

    def force_bus_off(self) -> None:
        self._ensure_attached()
        if not self._bus_off:
            self._bus_off = True
            self._stats.bus_off_events += 1
            log.warning("Bus-off forced on channel=%s", self.channel)

    def recover(self) -> None:
        self._ensure_attached()
        if self._bus_off:
            self._bus_off = False
            self._error_counter = 0
            self._stats.recoveries += 1
            log.info("Bus recovered on channel=%s", self.channel)

    def is_bus_off(self) -> bool:
        return self._bus_off

    def stats(self) -> BusStats:
        return self._stats
