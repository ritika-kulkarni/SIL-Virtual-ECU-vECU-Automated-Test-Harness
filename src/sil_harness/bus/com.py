"""AUTOSAR COM signal/PDU packing simulation."""

from __future__ import annotations

import struct

from sil_harness.bus.pdur import Pdu, PduR


class Com:
    def __init__(self, pdur: PduR) -> None:
        self.pdur = pdur
        self._signals: dict[str, int] = {}

    def send_signal(self, name: str, value: int, pdu_id: int = 4) -> bool:
        self._signals[name] = value
        payload = struct.pack(">I", value & 0xFFFFFFFF)
        return self.pdur.transmit(Pdu(pdu_id=pdu_id, data=payload))

    def receive_signal(self, name: str, timeout_ms: float = 50.0) -> int | None:
        pdu = self.pdur.receive(timeout_ms=timeout_ms)
        if pdu is None or len(pdu.data) < 4:
            return None
        value = struct.unpack(">I", pdu.data[:4])[0]
        self._signals[name] = value
        return value

    def send_raw(self, pdu_id: int, data: bytes) -> bool:
        return self.pdur.transmit(Pdu(pdu_id=pdu_id, data=data))

    def get_signal(self, name: str) -> int | None:
        return self._signals.get(name)
