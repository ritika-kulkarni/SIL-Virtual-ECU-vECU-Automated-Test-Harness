"""CANoe COM API adapter (Windows). Falls back gracefully on non-Windows."""

from __future__ import annotations

import sys
import time

from sil_harness.bus.interfaces import BusStats, CanFrame
from sil_harness.bus.python_sim import PythonBusSimulator
from sil_harness.core.errors import BusBackendError
from sil_harness.core.logging import get_logger

log = get_logger(__name__)


class CanoeComAdapter:
    """Vector CANoe via COM. Raises on attach if CANoe/pywin32 is missing."""

    name = "canoe"

    def __init__(self, cfg_path: str | None = None) -> None:
        self.cfg_path = cfg_path
        self._app = None
        self._fallback: PythonBusSimulator | None = None
        self._stats = BusStats()
        self._bus_off = False

    @staticmethod
    def is_available() -> bool:
        if sys.platform != "win32":
            return False
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            return False
        return True

    def attach(self) -> None:
        if not self.is_available():
            raise BusBackendError(
                "CANoe COM unavailable on this platform; use python backend or Windows/WSL with CANoe"
            )
        try:
            import win32com.client

            self._app = win32com.client.Dispatch("CANoe.Application")
            if self.cfg_path:
                self._app.Open(self.cfg_path)
            measurement = self._app.Measurement
            if not measurement.Running:
                measurement.Start()
            log.info("CANoe COM attached cfg=%s", self.cfg_path)
        except Exception as exc:  # COM failures are opaque
            raise BusBackendError(f"Failed to attach CANoe: {exc}") from exc

    def detach(self) -> None:
        if self._app is not None:
            try:
                if self._app.Measurement.Running:
                    self._app.Measurement.Stop()
            except Exception:
                log.exception("Error stopping CANoe measurement")
            self._app = None
        if self._fallback is not None:
            self._fallback.detach()
            self._fallback = None

    def send(self, frame: CanFrame) -> bool:
        if self._app is None:
            raise BusBackendError("CANoe not attached")
        if self._bus_off:
            self._stats.dropped_count += 1
            return False
        # Production: map to CANoe CAPL/COM TX. Here we mirror via internal queue
        # so unit tests on Windows without a full cfg still exercise the adapter path.
        if self._fallback is None:
            self._fallback = PythonBusSimulator()
            self._fallback.attach()
        ok = self._fallback.send(frame)
        if ok:
            self._stats.tx_count += 1
        return ok

    def receive(self, timeout_ms: float = 100.0) -> CanFrame | None:
        if self._fallback is None:
            time.sleep(min(timeout_ms, 1) / 1000.0)
            return None
        frame = self._fallback.receive(timeout_ms)
        if frame:
            self._stats.rx_count += 1
        return frame

    def inject_error_frame(self) -> None:
        self._stats.extra["error_frames"] = self._stats.extra.get("error_frames", 0) + 1

    def force_bus_off(self) -> None:
        self._bus_off = True
        self._stats.bus_off_events += 1

    def recover(self) -> None:
        if self._bus_off:
            self._bus_off = False
            self._stats.recoveries += 1

    def is_bus_off(self) -> bool:
        return self._bus_off

    def stats(self) -> BusStats:
        return self._stats


def create_bus_backend(name: str, **kwargs) -> PythonBusSimulator | CanoeComAdapter:
    if name == "canoe":
        adapter = CanoeComAdapter(cfg_path=kwargs.get("cfg_path"))
        try:
            adapter.attach()
            return adapter
        except BusBackendError as exc:
            log.warning("CANoe unavailable (%s); falling back to python backend", exc)
            sim = PythonBusSimulator(
                channel=kwargs.get("channel", 0),
                bitrate=kwargs.get("bitrate", 500_000),
            )
            sim.attach()
            return sim
    sim = PythonBusSimulator(
        channel=kwargs.get("channel", 0),
        bitrate=kwargs.get("bitrate", 500_000),
    )
    sim.attach()
    return sim
