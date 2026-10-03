# Tests

```
tests/
  unit/           # fast, no vecu_sim required
  integration/    # orchestrator + built binary
  conftest.py     # repo_root fixture
```

```bash
pytest tests/unit -q
pytest tests/integration -q
```

Integration tests look for `cmake` on `PATH` (including `.venv/bin`). Details: [docs/testing.md](../docs/testing.md).
