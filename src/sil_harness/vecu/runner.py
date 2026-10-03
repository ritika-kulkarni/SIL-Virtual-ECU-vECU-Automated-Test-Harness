"""Build and run the stub vECU binary."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from sil_harness.core.config import VecuConfig
from sil_harness.core.errors import VecuError
from sil_harness.core.logging import get_logger
from sil_harness.vecu.bridge import VecuBridge

log = get_logger(__name__)


class VecuRunner:
    def __init__(self, root: Path, cfg: VecuConfig) -> None:
        self.root = root
        self.cfg = cfg
        self._proc: subprocess.Popen[str] | None = None
        self.bridge: VecuBridge | None = None

    def build(self, coverage: bool = True) -> None:
        build_dir = self.root / self.cfg.build_dir
        build_dir.mkdir(parents=True, exist_ok=True)
        source_dir = self.root / "vecu"
        cmake_cmd = [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            f"-DCOVERAGE={'ON' if coverage else 'OFF'}",
            "-DBUILD_TESTS=ON",
        ]
        ninja = shutil.which("ninja")
        if ninja:
            cmake_cmd.extend(["-G", "Ninja", f"-DCMAKE_MAKE_PROGRAM={ninja}"])
        build_cmd = ["cmake", "--build", str(build_dir), "--target", "vecu_sim", "vecu_tests", "-j"]
        try:
            subprocess.run(cmake_cmd, check=True, capture_output=True, text=True)
            subprocess.run(build_cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise VecuError("cmake/compiler not available on PATH") from exc
        except subprocess.CalledProcessError as exc:
            raise VecuError(f"vECU build failed: {exc.stderr}") from exc
        log.info("vECU build complete at %s", build_dir)

    def start(self) -> VecuBridge:
        binary = self.root / self.cfg.binary
        if not binary.is_file():
            raise VecuError(f"vECU binary missing: {binary}; run build first")
        try:
            self._proc = subprocess.Popen(
                [str(binary), str(self.cfg.port)],
                cwd=str(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise VecuError(f"Failed to start vECU: {exc}") from exc

        deadline = time.monotonic() + self.cfg.startup_timeout_sec
        bridge = VecuBridge(self.cfg.host, self.cfg.port)
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
                raise VecuError(f"vECU exited early: {stderr}")
            try:
                bridge.connect(retries=1, delay=0.05)
                self.bridge = bridge
                return bridge
            except VecuError:
                time.sleep(0.1)
        raise VecuError("vECU startup timed out")

    def stop(self) -> None:
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def run_gtest(self) -> int:
        test_bin = self.root / self.cfg.build_dir / "vecu_tests"
        if not test_bin.is_file():
            raise VecuError(f"GTest binary missing: {test_bin}")
        result = subprocess.run([str(test_bin)], cwd=str(self.root))
        return result.returncode
