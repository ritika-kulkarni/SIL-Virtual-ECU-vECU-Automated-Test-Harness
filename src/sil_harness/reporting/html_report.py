"""HTML test report generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Template

from sil_harness.core.errors import SilHarnessError

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{{ project_name }} SIL Report</title>
  <style>
    body { font-family: Segoe UI, sans-serif; margin: 2rem; color: #1a1a1a; }
    h1 { margin-bottom: 0.2rem; }
    .meta { color: #555; margin-bottom: 1.5rem; }
    .summary { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
    .card { border: 1px solid #ddd; padding: 1rem 1.25rem; min-width: 10rem; }
    .pass { color: #0a7a28; font-weight: 600; }
    .fail { color: #b00020; font-weight: 600; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }
    th { background: #f5f5f5; }
    pre { background: #f7f7f7; padding: 0.75rem; overflow: auto; }
  </style>
</head>
<body>
  <h1>{{ project_name }} — SIL / vECU Report</h1>
  <div class="meta">Generated {{ generated_at }} | Backend: {{ backend }} | Build: {{ build_id }}</div>
  <div class="summary">
    <div class="card">Scenarios<br/><strong>{{ total }}</strong></div>
    <div class="card">Passed<br/><strong class="pass">{{ passed }}</strong></div>
    <div class="card">Failed<br/><strong class="fail">{{ failed }}</strong></div>
    <div class="card">Pass rate<br/><strong>{{ '%.1f'|format(pass_rate * 100) }}%</strong></div>
    <div class="card">Line cov<br/><strong>{{ '%.1f'|format(line_coverage * 100) }}%</strong></div>
    <div class="card">Branch cov<br/><strong>{{ '%.1f'|format(branch_coverage * 100) }}%</strong></div>
  </div>
  <table>
    <thead>
      <tr><th>Scenario</th><th>Verdict</th><th>Duration (s)</th><th>Details</th></tr>
    </thead>
    <tbody>
    {% for s in scenarios %}
      <tr>
        <td>{{ s.name }}</td>
        <td class="{{ 'pass' if s.passed else 'fail' }}">{{ 'PASS' if s.passed else 'FAIL' }}</td>
        <td>{{ '%.3f'|format(s.duration_sec) }}</td>
        <td><pre>{{ s.details }}</pre></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    duration_sec: float
    details: str
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportData:
    project_name: str
    backend: str
    build_id: str
    scenarios: list[ScenarioResult]
    line_coverage: float = 0.0
    branch_coverage: float = 0.0

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total) if self.total else 0.0


def render_html_report(data: ReportData, output_path: Path) -> Path:
    try:
        html = Template(REPORT_TEMPLATE).render(
            project_name=data.project_name,
            backend=data.backend,
            build_id=data.build_id,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
            total=data.total,
            passed=data.passed,
            failed=data.failed,
            pass_rate=data.pass_rate,
            line_coverage=data.line_coverage,
            branch_coverage=data.branch_coverage,
            scenarios=data.scenarios,
        )
    except Exception as exc:
        raise SilHarnessError(f"Failed to render HTML report: {exc}") from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
