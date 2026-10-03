#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT}/vecu/build"
OUT_DIR="${ROOT}/artifacts/coverage"
mkdir -p "$OUT_DIR"

if command -v lcov >/dev/null 2>&1; then
  lcov --capture --directory "$BUILD_DIR" --output-file "$OUT_DIR/coverage.info" --rc lcov_branch_coverage=1 || true
  if command -v genhtml >/dev/null 2>&1 && [[ -f "$OUT_DIR/coverage.info" ]]; then
    genhtml "$OUT_DIR/coverage.info" --branch-coverage --output-directory "$OUT_DIR/html" || true
  fi
fi

if command -v gcovr >/dev/null 2>&1; then
  gcovr -r "$ROOT/vecu" "$BUILD_DIR" --html --html-details -o "$OUT_DIR/gcovr.html" || true
fi

# Ensure a simple index exists for the harness publisher
if [[ ! -f "$OUT_DIR/index.html" ]]; then
  python3 - <<'PY'
from pathlib import Path
from sil_harness.reporting.coverage import generate_lcov, parse_coverage_summary, write_coverage_html
root = Path(".")
info = generate_lcov(root / "vecu/build", root / "artifacts/coverage/coverage.info")
summary = parse_coverage_summary(info)
write_coverage_html(summary, root / "artifacts/coverage")
print(f"line={summary.line_coverage:.2%} branch={summary.branch_coverage:.2%}")
PY
fi

echo "Coverage artifacts in $OUT_DIR"
