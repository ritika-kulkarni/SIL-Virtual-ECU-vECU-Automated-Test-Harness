# Scripts

| Script | What it does |
|--------|----------------|
| `run_local.sh` | venv-aware full local pipeline (cmake, gtest, pytest, SIL, coverage, mock publish) |
| `generate_coverage.sh` | lcov/gcovr if present, else harness synthesizer |

```bash
bash scripts/run_local.sh
bash scripts/generate_coverage.sh
```

Both expect to be run from a checkout where `pip install -e ".[dev]"` has been done (or they install it).
