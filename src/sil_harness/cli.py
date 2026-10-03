"""CLI for local runs — same stages Jenkins hits."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from sil_harness.core.config import load_harness_config
from sil_harness.core.logging import setup_logging
from sil_harness.pipeline.orchestrator import Orchestrator


def _parse_scenarios(value: str | None) -> list[str] | None:
    if value is None or value.strip().lower() == "all":
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@click.group()
@click.option("--log-level", default="INFO", show_default=True)
@click.option("--json-logs", is_flag=True, help="Emit structured JSON logs")
def main(log_level: str, json_logs: bool) -> None:
    """SIL / Virtual ECU automated test harness."""
    setup_logging(level=log_level, json_logs=json_logs)


@main.command("run")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, exists=True),
    default=Path("config/harness.yaml"),
    show_default=True,
)
@click.option("--scenarios", default="all", help="Comma-separated scenario names or 'all'")
@click.option("--skip-build", is_flag=True, help="Skip vECU CMake build")
@click.option("--skip-vecu", is_flag=True, help="Do not start vECU process")
@click.option("--no-gate", is_flag=True, help="Do not fail on quality gate thresholds")
def run_cmd(
    config_path: Path,
    scenarios: str,
    skip_build: bool,
    skip_vecu: bool,
    no_gate: bool,
) -> None:
    """Execute SIL scenarios, produce HTML report and coverage."""
    cfg = load_harness_config(config_path)
    orch = Orchestrator(cfg)
    report = orch.run(
        _parse_scenarios(scenarios),
        build_vecu=not skip_build,
        start_vecu=not skip_vecu,
        collect_coverage=True,
    )
    click.echo(
        f"Completed {report.total} scenarios: {report.passed} passed, {report.failed} failed "
        f"(pass_rate={report.pass_rate:.0%}, line={report.line_coverage:.0%}, "
        f"branch={report.branch_coverage:.0%})"
    )
    if not no_gate and not orch.evaluate_gates(report):
        sys.exit(2)
    if report.failed:
        sys.exit(1)


@main.command("report")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, exists=True),
    default=Path("config/harness.yaml"),
    show_default=True,
)
def report_cmd(config_path: Path) -> None:
    """Print path to the latest HTML report."""
    cfg = load_harness_config(config_path)
    path = Path(cfg.reporting.html_report)
    if not path.is_file():
        click.echo(f"Report not found: {path}", err=True)
        sys.exit(1)
    click.echo(str(path.resolve()))


@main.command("publish")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, exists=True),
    default=Path("config/harness.yaml"),
    show_default=True,
)
@click.option("--branch", default="local", show_default=True)
def publish_cmd(config_path: Path, branch: str) -> None:
    """Publish HTML report and coverage to Artifactory (or local mock)."""
    cfg = load_harness_config(config_path)
    orch = Orchestrator(cfg)
    urls = orch.publish(branch=branch)
    if not urls:
        click.echo("No artifacts published", err=True)
        sys.exit(1)
    for url in urls:
        click.echo(url)


if __name__ == "__main__":
    main()
