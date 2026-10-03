from pathlib import Path

import pytest

from sil_harness.core.config import load_harness_config, load_scenarios
from sil_harness.core.errors import ConfigError


def test_load_harness_config(harness_config_path: Path) -> None:
    cfg = load_harness_config(harness_config_path)
    assert cfg.project_name == "sil-vecu-harness"
    assert "frame_drop" in cfg.scenarios


def test_load_scenarios(harness_config_path: Path) -> None:
    cfg = load_harness_config(harness_config_path)
    scenarios = load_scenarios(cfg)
    assert len(scenarios) == 3
    assert {s.name for s in scenarios} == {
        "frame_drop",
        "bus_off",
        "j1939_tp_retransmit",
    }


def test_missing_config(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_harness_config(tmp_path / "missing.yaml")


def test_empty_scenario_list(harness_config_path: Path) -> None:
    cfg = load_harness_config(harness_config_path)
    with pytest.raises(ConfigError):
        load_scenarios(cfg, names=[])
