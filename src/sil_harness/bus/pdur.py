"""AUTOSAR PduR routing simulation."""

from __future__ import annotations

from dataclasses import dataclass

from sil_harness.bus.canif import CanIf
from sil_harness.bus.interfaces import CanFrame


@dataclass
class Pdu:
    pdu_id: int
    data: bytes


class PduR:
    """Routes PDUs between COM and CanIf using a static routing table."""

    def __init__(self, canif: CanIf, routes: dict[int, int] | None = None) -> None:
        # pdu_id -> can_id
        self.routes = routes or {
            1: 0x18EAFF00,  # request
            2: 0x18ECFF00,  # TP.CM
            3: 0x18EBFF00,  # TP.DT
            4: 0x18FF1200,  # app PDU
        }
        self.canif = canif
        self._rx_buffer: list[Pdu] = []

    def transmit(self, pdu: Pdu) -> bool:
        can_id = self.routes.get(pdu.pdu_id)
        if can_id is None:
            return False
        return self.canif.transmit(can_id, pdu.data)

    def indicate(self, frame: CanFrame) -> Pdu | None:
        for pdu_id, can_id in self.routes.items():
            if can_id == frame.can_id:
                pdu = Pdu(pdu_id=pdu_id, data=frame.data)
                self._rx_buffer.append(pdu)
                return pdu
        return None

    def receive(self, timeout_ms: float = 50.0) -> Pdu | None:
        frame = self.canif.receive(timeout_ms=timeout_ms)
        if frame is None:
            return None
        return self.indicate(frame)
