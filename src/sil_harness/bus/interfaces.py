"""Bus backend protocol and shared frame models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class CanFrame:
    can_id: int
    data: bytes
    is_extended: bool = True
    timestamp_ms: float = 0.0


@dataclass
class BusStats:
    tx_count: int = 0
    rx_count: int = 0
    dropped_count: int = 0
    bus_off_events: int = 0
    recoveries: int = 0
    tp_retries: int = 0
    extra: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class BusBackend(Protocol):
    name: str

    def attach(self) -> None: ...

    def detach(self) -> None: ...

    def send(self, frame: CanFrame) -> bool: ...

    def receive(self, timeout_ms: float = 100.0) -> CanFrame | None: ...

    def inject_error_frame(self) -> None: ...

    def force_bus_off(self) -> None: ...

    def recover(self) -> None: ...

    def is_bus_off(self) -> bool: ...

    def stats(self) -> BusStats: ...
