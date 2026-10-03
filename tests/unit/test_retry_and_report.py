from pathlib import Path

import pytest

from sil_harness.core.config import RetryConfig
from sil_harness.core.errors import PublishError, SilHarnessError
from sil_harness.core.retry import call_with_retry
from sil_harness.reporting.artifactory import LocalMockArtifactory, create_artifactory_client
from sil_harness.reporting.coverage import parse_coverage_summary, write_coverage_html
from sil_harness.reporting.html_report import ReportData, ScenarioResult, render_html_report
from sil_harness.core.config import ArtifactoryConfig


def test_retry_eventually_succeeds() -> None:
    state = {"n": 0}

    def flaky() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise SilHarnessError("transient")
        return "ok"

    result = call_with_retry(flaky, RetryConfig(max_attempts=3, initial_delay_sec=0.01, max_delay_sec=0.05))
    assert result == "ok"
    assert state["n"] == 3


def test_retry_exhaustion() -> None:
    def always_fail() -> None:
        raise SilHarnessError("nope")

    with pytest.raises(SilHarnessError):
        call_with_retry(
            always_fail,
            RetryConfig(max_attempts=2, initial_delay_sec=0.01, max_delay_sec=0.02),
        )


def test_html_report(tmp_path: Path) -> None:
    data = ReportData(
        project_name="demo",
        backend="python",
        build_id="1",
        scenarios=[
            ScenarioResult("frame_drop", True, 0.1, "{}"),
            ScenarioResult("bus_off", False, 0.2, "fail"),
        ],
        line_coverage=0.8,
        branch_coverage=0.7,
    )
    out = render_html_report(data, tmp_path / "report.html")
    text = out.read_text(encoding="utf-8")
    assert "frame_drop" in text
    assert "PASS" in text
    assert "FAIL" in text


def test_mock_artifactory(tmp_path: Path) -> None:
    src = tmp_path / "a.html"
    src.write_text("<html></html>", encoding="utf-8")
    client = LocalMockArtifactory(tmp_path / "repo")
    uri = client.upload(src, "branch/1/a.html")
    assert (tmp_path / "repo" / "branch" / "1" / "a.html").is_file()
    assert uri.startswith("file://")


def test_mock_artifactory_missing_file(tmp_path: Path) -> None:
    client = LocalMockArtifactory(tmp_path / "repo")
    with pytest.raises(PublishError):
        client.upload(tmp_path / "missing.txt", "x")


def test_create_artifactory_mock_mode(tmp_path: Path) -> None:
    cfg = ArtifactoryConfig(mode="mock", local_root=tmp_path / "art")
    client = create_artifactory_client(cfg, RetryConfig())
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    client.upload(f, "r/f.txt")


def test_coverage_parse_and_html(tmp_path: Path) -> None:
    info = tmp_path / "coverage.info"
    info.write_text("TN:\nSF:x\nLH:80\nLF:100\nBRH:30\nBRF:40\nend_of_record\n", encoding="utf-8")
    summary = parse_coverage_summary(info)
    assert summary.line_coverage == pytest.approx(0.8)
    assert summary.branch_coverage == pytest.approx(0.75)
    index = write_coverage_html(summary, tmp_path / "html")
    assert index.is_file()
