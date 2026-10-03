"""J1939 transport protocol (BAM/CMDT) with retransmission support."""

from __future__ import annotations

from dataclasses import dataclass, field

from sil_harness.bus.canif import CanIf
from sil_harness.bus.interfaces import CanFrame
from sil_harness.core.errors import BusBackendError
from sil_harness.core.logging import get_logger

log = get_logger(__name__)

PGN_TP_CM = 0xEC00
PGN_TP_DT = 0xEB00
CM_RTS = 0x10
CM_CTS = 0x11
CM_ACK = 0x13
CM_BAM = 0x20
CM_ABORT = 0xFF


def _can_id(pgn: int, sa: int, da: int = 0xFF) -> int:
    # Priority 6, DP/EDP 0
    return (6 << 26) | (pgn << 8) | sa | ((da & 0xFF) << 8) if pgn in (PGN_TP_CM, PGN_TP_DT) else (
        (6 << 26) | (pgn << 8) | sa
    )


def make_tp_cm_id(sa: int, da: int) -> int:
    return (6 << 26) | (0xEC << 16) | (da << 8) | sa


def make_tp_dt_id(sa: int, da: int) -> int:
    return (6 << 26) | (0xEB << 16) | (da << 8) | sa


@dataclass
class TpSessionResult:
    delivered: bool
    retries: int
    abort: bool = False
    bytes_delivered: int = 0
    control_frames_sent: int = 0
    data_frames_sent: int = 0
    notes: list[str] = field(default_factory=list)


class J1939Transport:
    """Minimal CMDT (RTS/CTS/ACK) sender with forced control-frame drops."""

    def __init__(
        self,
        canif: CanIf,
        source_address: int = 0x80,
        dest_address: int = 0xF9,
        max_retries: int = 3,
    ) -> None:
        self.canif = canif
        self.sa = source_address
        self.da = dest_address
        self.max_retries = max_retries
        self._drop_control_remaining = 0
        self.retries_observed = 0

    def force_control_drops(self, count: int) -> None:
        self._drop_control_remaining = max(0, count)

    def _send_control(self, data: bytes) -> bool:
        frame = CanFrame(can_id=make_tp_cm_id(self.sa, self.da), data=data)
        if self._drop_control_remaining > 0:
            self._drop_control_remaining -= 1
            log.info("Injected TP control-frame drop remaining=%s", self._drop_control_remaining)
            return False
        return self.canif.transmit(frame.can_id, frame.data)

    def _send_data(self, seq: int, chunk: bytes) -> bool:
        payload = bytes([seq]) + chunk.ljust(7, b"\x00")
        return self.canif.transmit(make_tp_dt_id(self.sa, self.da), payload)

    def send_message(self, payload: bytes, pgn: int = 0xFF12) -> TpSessionResult:
        if not payload:
            raise BusBackendError("J1939 TP payload must be non-empty")

        total = len(payload)
        packets = (total + 6) // 7
        result = TpSessionResult(delivered=False, retries=0)

        attempt = 0
        while attempt <= self.max_retries:
            rts = bytes(
                [
                    CM_RTS,
                    total & 0xFF,
                    (total >> 8) & 0xFF,
                    packets & 0xFF,
                    0xFF,
                    pgn & 0xFF,
                    (pgn >> 8) & 0xFF,
                    (pgn >> 16) & 0xFF,
                ]
            )
            if not self._send_control(rts):
                attempt += 1
                result.retries = attempt
                self.retries_observed = attempt
                result.notes.append(f"RTS dropped attempt={attempt}")
                continue

            result.control_frames_sent += 1

            # Simulate peer CTS (in SIL we loop it back / accept locally)
            cts_ok = True
            if self._drop_control_remaining > 0:
                self._drop_control_remaining -= 1
                cts_ok = False
                result.notes.append("CTS lost")

            if not cts_ok:
                attempt += 1
                result.retries = attempt
                self.retries_observed = attempt
                continue

            for i in range(packets):
                chunk = payload[i * 7 : (i + 1) * 7]
                if not self._send_data(i + 1, chunk):
                    attempt += 1
                    result.retries = attempt
                    self.retries_observed = attempt
                    result.notes.append(f"DT drop seq={i+1}")
                    break
                result.data_frames_sent += 1
            else:
                # ACK
                ack = bytes(
                    [
                        CM_ACK,
                        total & 0xFF,
                        (total >> 8) & 0xFF,
                        packets & 0xFF,
                        0xFF,
                        pgn & 0xFF,
                        (pgn >> 8) & 0xFF,
                        (pgn >> 16) & 0xFF,
                    ]
                )
                if self._drop_control_remaining > 0:
                    self._drop_control_remaining -= 1
                    attempt += 1
                    result.retries = attempt
                    self.retries_observed = attempt
                    result.notes.append("ACK dropped")
                    continue
                self.canif.transmit(make_tp_cm_id(self.da, self.sa), ack)
                result.control_frames_sent += 1
                result.delivered = True
                result.bytes_delivered = total
                return result

        result.abort = True
        result.notes.append("TP aborted after max retries")
        return result
