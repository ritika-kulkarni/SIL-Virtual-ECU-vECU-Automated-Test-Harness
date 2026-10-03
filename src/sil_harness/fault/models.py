"""Fault injection result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FaultResult:
    fault_type: str
    applied: bool
    details: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float | int | bool] = field(default_factory=dict)
