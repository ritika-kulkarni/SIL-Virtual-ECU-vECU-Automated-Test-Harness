#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer project venv tools when present
if [[ -d "$ROOT/.venv/bin" ]]; then
  export PATH="$ROOT/.venv/bin:$PATH"
fi

python3 -m pip install -e ".[dev]" -q
python3 -m pip install cmake ninja -q >/dev/null 2>&1 || true

echo "==> Building vECU + GTest"
GENERATOR_ARGS=()
if command -v ninja >/dev/null 2>&1; then
  GENERATOR_ARGS=(-G Ninja -DCMAKE_MAKE_PROGRAM="$(command -v ninja)")
fi
cmake -S vecu -B vecu/build "${GENERATOR_ARGS[@]}" -DCOVERAGE=ON -DBUILD_TESTS=ON
cmake --build vecu/build -j
./vecu/build/vecu_tests

echo "==> Running Python unit tests"
pytest tests/unit -q

echo "==> Running SIL harness"
sil-harness run --config config/harness.yaml --scenarios all --skip-build

echo "==> Generating coverage pages"
bash scripts/generate_coverage.sh

echo "==> Publishing artifacts (mock Artifactory)"
sil-harness publish --config config/harness.yaml --branch local

echo "Done. Report: artifacts/reports/sil_report.html"
