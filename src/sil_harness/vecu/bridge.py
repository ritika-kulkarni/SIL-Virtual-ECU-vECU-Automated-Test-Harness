"""TCP bridge to the stub vECU process."""

from __future__ import annotations

import socket
import time

from sil_harness.core.errors import VecuError
from sil_harness.core.logging import get_logger

log = get_logger(__name__)


class VecuBridge:
    def __init__(self, host: str = "127.0.0.1", port: int = 19000, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    def connect(self, retries: int = 10, delay: float = 0.2) -> None:
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                sock.settimeout(self.timeout)
                self._sock = sock
                reply = self.command("PING")
                if not reply.startswith("PONG"):
                    raise VecuError(f"Unexpected ping reply: {reply}")
                log.info("Connected to vECU %s:%s", self.host, self.port)
                return
            except OSError as exc:
                last_exc = exc
                time.sleep(delay * attempt)
        raise VecuError(f"Unable to connect to vECU at {self.host}:{self.port}: {last_exc}")

    def close(self) -> None:
        if self._sock is not None:
            try:
                self.command("QUIT")
            except Exception:
                pass
            try:
                self._sock.close()
            finally:
                self._sock = None

    def command(self, line: str) -> str:
        if self._sock is None:
            raise VecuError("vECU bridge not connected")
        payload = (line.strip() + "\n").encode("utf-8")
        self._sock.sendall(payload)
        data = self._sock.recv(4096)
        if not data:
            raise VecuError("vECU closed connection")
        return data.decode("utf-8", errors="replace").strip()
