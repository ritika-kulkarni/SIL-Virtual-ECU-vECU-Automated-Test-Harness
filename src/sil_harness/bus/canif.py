"""AUTOSAR CanIf layer simulation."""

from __future__ import annotations

from sil_harness.bus.interfaces import BusBackend, CanFrame
from sil_harness.core.errors import BusBackendError


class CanIf:
    def __init__(self, bus: BusBackend) -> None:
        self.bus = bus
        self._tx_confirmations = 0
        self._rx_indications = 0

    def transmit(self, can_id: int, data: bytes, is_extended: bool = True) -> bool:
        if self.bus.is_bus_off():
            return False
        ok = self.bus.send(CanFrame(can_id=can_id, data=data, is_extended=is_extended))
        if ok:
            self._tx_confirmations += 1
        return ok

    def receive(self, timeout_ms: float = 50.0) -> CanFrame | None:
        frame = self.bus.receive(timeout_ms=timeout_ms)
        if frame is not None:
            self._rx_indications += 1
        return frame

    def get_status(self) -> str:
        return "BUS_OFF" if self.bus.is_bus_off() else "ONLINE"

    @property
    def tx_confirmations(self) -> int:
        return self._tx_confirmations

    @property
    def rx_indications(self) -> int:
        return self._rx_indications

    def ensure_online(self) -> None:
        if self.bus.is_bus_off():
            raise BusBackendError("CanIf offline (bus-off)")
