# Config

| File | Purpose |
|------|---------|
| `harness.yaml` | project knobs: backend, bus, thresholds, Artifactory, scenario list |
| `scenarios/*.yaml` | per-fault expectations |

```bash
sil-harness run --config config/harness.yaml --scenarios all
sil-harness run --config config/harness.yaml --scenarios frame_drop,bus_off
```

Gate thresholds live under `thresholds:` (`min_pass_rate`, `min_line_coverage`, `min_branch_coverage`, `scenario_timeout_sec`).

Scenario field reference: [docs/scenarios.md](../docs/scenarios.md).
