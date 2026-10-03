from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from sil_harness.core.config import load_harness_config
from sil_harness.pipeline.orchestrator import Orchestrator

def _toolchain_available(repo_root: Path) -> bool:
    path = os.environ.get("PATH", "")
    venv_bin = str(repo_root / ".venv" / "bin")
    search_path = venv_bin + os.pathsep + path
    cmake = shutil.which("cmake", path=search_path)
    compiler = shutil.which("gcc", path=search_path) or shutil.which("clang", path=search_path)
    return bool(cmake and compiler)


@pytest.mark.integration
def test_full_sil_pipeline(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not _toolchain_available(repo_root):
        pytest.skip("cmake/compiler required for integration")

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("PATH", str(repo_root / ".venv" / "bin") + os.pathsep + os.environ.get("PATH", ""))
    cfg = load_harness_config(repo_root / "config" / "harness.yaml")
    # Isolate artifacts under tmp while keeping vecu sources
    cfg.reporting.output_dir = tmp_path / "reports"
    cfg.reporting.html_report = tmp_path / "reports" / "sil_report.html"
    cfg.reporting.coverage_dir = tmp_path / "coverage"
    cfg.artifactory.mode = "mock"
    cfg.artifactory.local_root = tmp_path / "artifactory"
    cfg.vecu.port = 19041  # avoid clashes
    cfg.vecu.binary = Path("vecu/build/vecu_sim")

    orch = Orchestrator(cfg)
    # Reuse existing build if present to avoid path/generator issues in odd workspace names
    build_needed = not (repo_root / "vecu" / "build" / "vecu_sim").is_file()
    report = orch.run(build_vecu=build_needed, start_vecu=True, collect_coverage=True)

    assert report.total == 3
    assert report.failed == 0
    assert report.pass_rate == 1.0
    assert cfg.reporting.html_report.is_file()
    assert (cfg.reporting.output_dir / "summary.json").is_file()
    assert orch.evaluate_gates(report)

    urls = orch.publish(branch="ci-test")
    assert urls
    assert any("sil_report.html" in u or "summary.json" in u or "coverage" in u for u in urls)


@pytest.mark.integration
def test_canoe_backend_falls_back(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg = load_harness_config(repo_root / "config" / "harness.yaml")
    cfg.backend = "canoe"
    from sil_harness.bus.canoe_adapter import create_bus_backend

    bus = create_bus_backend("canoe")
    assert bus.name == "python"
    bus.detach()
