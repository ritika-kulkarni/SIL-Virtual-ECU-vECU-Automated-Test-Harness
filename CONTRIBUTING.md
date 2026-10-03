# Contributing

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If you do not have system cmake/ninja:

```bash
pip install cmake ninja
```

## Before you open a PR

```bash
pytest tests/unit -q
bash scripts/run_local.sh    # or at least sil-harness run --scenarios all
```

If you touched the C stack, also run `./vecu/build/vecu_tests`.

## Style notes

- Keep scenario YAML boring and explicit — magic numbers belong in the YAML, not buried in Python.
- Prefer failing with a typed error from `sil_harness.core.errors` over a bare `Exception`.
- Do not commit `artifacts/`, `vecu/build/`, or `.venv/`.

## Commit messages

Short imperative subject is fine. Say why when it is not obvious from the diff.

Examples:

- `add bus-off recovery check to CanIf tests`
- `fix j1939 TP retry count when CTS is dropped twice`
- `wire mock artifactory publish into jenkins post stage`
