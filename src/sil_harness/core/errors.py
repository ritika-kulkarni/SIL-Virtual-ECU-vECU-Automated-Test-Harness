"""Harness-specific exceptions."""

from __future__ import annotations


class SilHarnessError(Exception):
    """Anything that went wrong inside the harness."""


class ConfigError(SilHarnessError):
    """Bad or missing config / scenario YAML."""


class BusTimeout(SilHarnessError):
    """TX/RX waited too long."""


class BusBackendError(SilHarnessError):
    """Attach / send / receive failed on the bus backend."""


class FaultInjectionError(SilHarnessError):
    """Fault injector misconfigured or could not apply the fault."""


class VecuError(SilHarnessError):
    """vECU build, start, or TCP bridge problem."""


class ScenarioError(SilHarnessError):
    """Scenario blew up outside of a normal FAIL verdict."""


class PublishError(SilHarnessError):
    """Could not publish artifacts."""


class CoverageError(SilHarnessError):
    """Could not collect or parse coverage."""
