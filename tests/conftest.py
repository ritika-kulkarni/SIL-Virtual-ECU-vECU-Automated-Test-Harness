from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def harness_config_path(repo_root: Path) -> Path:
    return repo_root / "config" / "harness.yaml"
