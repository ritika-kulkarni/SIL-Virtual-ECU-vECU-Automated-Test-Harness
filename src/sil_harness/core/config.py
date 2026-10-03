"""Pydantic configuration models for the SIL harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from sil_harness.core.errors import ConfigError


class BusConfig(BaseModel):
    channel: int = 0
    bitrate: int = 500_000
    j1939_source_address: int = 0x80
    j1939_dest_address: int = 0xF9


class ThresholdConfig(BaseModel):
    min_pass_rate: float = 1.0
    min_line_coverage: float = 0.70
    min_branch_coverage: float = 0.60
    scenario_timeout_sec: float = 30.0


class RetryConfig(BaseModel):
    max_attempts: int = 3
    initial_delay_sec: float = 0.5
    max_delay_sec: float = 8.0


class ArtifactoryConfig(BaseModel):
    mode: Literal["mock", "http"] = "mock"
    base_url: str = "https://artifactory.example.com/artifactory"
    repository: str = "sil-reports"
    local_root: Path = Path("artifacts/artifactory")
    username_env: str = "ARTIFACTORY_USER"
    password_env: str = "ARTIFACTORY_PASSWORD"


class VecuConfig(BaseModel):
    build_dir: Path = Path("vecu/build")
    binary: Path = Path("vecu/build/vecu_sim")
    host: str = "127.0.0.1"
    port: int = 19000
    startup_timeout_sec: float = 10.0


class ReportingConfig(BaseModel):
    output_dir: Path = Path("artifacts/reports")
    html_report: Path = Path("artifacts/reports/sil_report.html")
    coverage_dir: Path = Path("artifacts/coverage")


class FaultSpec(BaseModel):
    type: Literal["frame_drop", "bus_off", "j1939_tp_retransmit"]
    drop_rate: float = 0.0
    can_ids: list[int] = Field(default_factory=list)
    window_ms: int = 0
    error_frames_before_bus_off: int = 32
    recovery_window_ms: int = 1000
    drop_control_frames: int = 0
    max_tp_retries: int = 3
    payload_bytes: int = 40


class Expectations(BaseModel):
    min_frames_received: int = 0
    max_drop_ratio: float = 1.0
    require_recovery: bool = False
    require_bus_off: bool = False
    max_recovery_ms: int = 0
    require_retransmit: bool = False
    require_delivery: bool = False
    max_retries_observed: int = 0


class ScenarioConfig(BaseModel):
    name: str
    description: str = ""
    fault: FaultSpec
    expectations: Expectations = Field(default_factory=Expectations)


class HarnessConfig(BaseModel):
    project_name: str = "sil-vecu-harness"
    backend: Literal["python", "canoe"] = "python"
    bus: BusConfig = Field(default_factory=BusConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    artifactory: ArtifactoryConfig = Field(default_factory=ArtifactoryConfig)
    vecu: VecuConfig = Field(default_factory=VecuConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    scenarios: list[str] = Field(default_factory=list)
    root: Path = Path(".")

    @field_validator("scenarios")
    @classmethod
    def _non_empty_names(cls, value: list[str]) -> list[str]:
        cleaned = [s.strip() for s in value if s and s.strip()]
        return cleaned


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Expected mapping at root of {path}")
    return data


def load_harness_config(path: Path | str) -> HarnessConfig:
    config_path = Path(path).resolve()
    data = _load_yaml(config_path)
    cfg = HarnessConfig.model_validate(data)
    cfg.root = config_path.parent.parent if config_path.parent.name == "config" else config_path.parent
    return cfg


def load_scenario(path: Path | str) -> ScenarioConfig:
    data = _load_yaml(Path(path))
    try:
        return ScenarioConfig.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise ConfigError(f"Invalid scenario file {path}: {exc}") from exc


def load_scenarios(cfg: HarnessConfig, names: list[str] | None = None) -> list[ScenarioConfig]:
    selected = names if names is not None else cfg.scenarios
    if not selected:
        raise ConfigError("No scenarios selected; configure harness.yaml or pass --scenarios")

    scenario_dir = cfg.root / "config" / "scenarios"
    loaded: list[ScenarioConfig] = []
    for name in selected:
        path = scenario_dir / f"{name}.yaml"
        if not path.is_file():
            raise ConfigError(f"Scenario '{name}' not found at {path}")
        loaded.append(load_scenario(path))
    return loaded
