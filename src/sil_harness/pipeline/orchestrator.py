"""Runs scenarios end-to-end: bus + faults + report + gates."""

from __future__ import annotations

import json
import os
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from sil_harness.bus.canoe_adapter import create_bus_backend
from sil_harness.core.config import HarnessConfig, ScenarioConfig, load_scenarios
from sil_harness.core.errors import ScenarioError, SilHarnessError
from sil_harness.core.logging import get_logger
from sil_harness.fault.injector import FaultInjector
from sil_harness.reporting.artifactory import create_artifactory_client
from sil_harness.reporting.coverage import (
    CoverageSummary,
    generate_lcov,
    parse_coverage_summary,
    write_coverage_html,
)
from sil_harness.reporting.html_report import ReportData, ScenarioResult, render_html_report
from sil_harness.vecu.runner import VecuRunner

log = get_logger(__name__)


class Orchestrator:
    def __init__(self, cfg: HarnessConfig) -> None:
        self.cfg = cfg
        self.results: list[ScenarioResult] = []
        self.coverage: CoverageSummary | None = None
        self.backend_name = cfg.backend

    def run(
        self,
        scenario_names: list[str] | None = None,
        *,
        build_vecu: bool = True,
        start_vecu: bool = True,
        collect_coverage: bool = True,
    ) -> ReportData:
        scenarios = load_scenarios(self.cfg, scenario_names)
        runner = VecuRunner(self.cfg.root, self.cfg.vecu)
        bridge = None

        try:
            if build_vecu:
                runner.build(coverage=True)
                gtest_rc = runner.run_gtest()
                if gtest_rc != 0:
                    raise ScenarioError(f"vECU GTest failed with code {gtest_rc}")

            if start_vecu:
                bridge = runner.start()
                # Smoke the control plane
                status = bridge.command("STATUS")
                log.info("vECU status: %s", status)

            bus = create_bus_backend(
                self.cfg.backend,
                channel=self.cfg.bus.channel,
                bitrate=self.cfg.bus.bitrate,
            )
            self.backend_name = getattr(bus, "name", self.cfg.backend)
            injector = FaultInjector(bus)

            for scenario in scenarios:
                self.results.append(self._run_scenario(injector, scenario))

            bus.detach()

            if collect_coverage:
                self.coverage = self._collect_coverage()

            report = self._build_report()
            render_html_report(report, Path(self.cfg.reporting.html_report))
            self._write_json_summary(report)
            return report
        except SilHarnessError:
            raise
        except Exception as exc:
            raise ScenarioError(
                f"Unexpected orchestrator failure: {exc}\n{traceback.format_exc()}"
            ) from exc
        finally:
            if bridge is not None:
                runner.stop()

    def _run_scenario(self, injector: FaultInjector, scenario: ScenarioConfig) -> ScenarioResult:
        log.info("Starting scenario=%s", scenario.name)
        started = time.monotonic()
        try:
            # Soft timeout via wall clock check after apply (scenarios are short)
            result = injector.apply(scenario.fault, scenario.expectations)
            duration = time.monotonic() - started
            if duration > self.cfg.thresholds.scenario_timeout_sec:
                raise ScenarioError(
                    f"Scenario {scenario.name} exceeded timeout "
                    f"({duration:.1f}s > {self.cfg.thresholds.scenario_timeout_sec}s)"
                )
            passed = bool(result.metrics.get("passed", False))
            details = json.dumps({"details": result.details, "metrics": result.metrics}, indent=2)
            return ScenarioResult(
                name=scenario.name,
                passed=passed,
                duration_sec=duration,
                details=details,
                metrics=dict(result.metrics),
            )
        except Exception as exc:
            duration = time.monotonic() - started
            log.exception("Scenario %s failed", scenario.name)
            return ScenarioResult(
                name=scenario.name,
                passed=False,
                duration_sec=duration,
                details=f"{type(exc).__name__}: {exc}",
                metrics={"passed": False},
            )

    def _collect_coverage(self) -> CoverageSummary:
        build_dir = self.cfg.root / self.cfg.vecu.build_dir
        cov_dir = Path(self.cfg.reporting.coverage_dir)
        info = generate_lcov(build_dir, cov_dir / "coverage.info")
        summary = parse_coverage_summary(info)
        write_coverage_html(summary, cov_dir)
        return summary

    def _build_report(self) -> ReportData:
        line_cov = self.coverage.line_coverage if self.coverage else 0.0
        branch_cov = self.coverage.branch_coverage if self.coverage else 0.0
        return ReportData(
            project_name=self.cfg.project_name,
            backend=self.backend_name,
            build_id=os.environ.get("BUILD_ID", os.environ.get("BUILD_NUMBER", "local")),
            scenarios=self.results,
            line_coverage=line_cov,
            branch_coverage=branch_cov,
        )

    def _write_json_summary(self, report: ReportData) -> None:
        out = Path(self.cfg.reporting.output_dir) / "summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "project_name": report.project_name,
            "backend": report.backend,
            "build_id": report.build_id,
            "pass_rate": report.pass_rate,
            "line_coverage": report.line_coverage,
            "branch_coverage": report.branch_coverage,
            "scenarios": [asdict(s) for s in report.scenarios],
            "gates": {
                "pass_rate_ok": report.pass_rate >= self.cfg.thresholds.min_pass_rate,
                "line_coverage_ok": report.line_coverage >= self.cfg.thresholds.min_line_coverage,
                "branch_coverage_ok": report.branch_coverage
                >= self.cfg.thresholds.min_branch_coverage,
            },
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def publish(self, branch: str = "local") -> list[str]:
        client = create_artifactory_client(self.cfg.artifactory, self.cfg.retry)
        build_id = os.environ.get("BUILD_ID", os.environ.get("BUILD_NUMBER", "local"))
        prefix = f"{branch}/{build_id}"
        uploaded: list[str] = []
        targets = [
            Path(self.cfg.reporting.html_report),
            Path(self.cfg.reporting.output_dir) / "summary.json",
            Path(self.cfg.reporting.coverage_dir),
        ]
        for path in targets:
            if not path.exists():
                log.warning("Skip missing artifact %s", path)
                continue
            remote = f"{prefix}/{path.name}"
            uploaded.append(client.upload(path, remote))
        return uploaded

    def evaluate_gates(self, report: ReportData) -> bool:
        ok = (
            report.pass_rate >= self.cfg.thresholds.min_pass_rate
            and report.line_coverage >= self.cfg.thresholds.min_line_coverage
            and report.branch_coverage >= self.cfg.thresholds.min_branch_coverage
        )
        if not ok:
            log.error(
                "Quality gates failed pass_rate=%.2f line=%.2f branch=%.2f",
                report.pass_rate,
                report.line_coverage,
                report.branch_coverage,
            )
        return ok
