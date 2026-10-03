# Fault injection scenarios

Scenarios are YAML under `config/scenarios/`. The harness loads whatever list is in `config/harness.yaml` (or whatever you pass to `--scenarios`).

## frame_drop

Drops a percentage of frames for selected CAN IDs during a short window, then checks that some traffic still got through and the bus did not stay wedged.

| Field | Notes |
|-------|-------|
| `drop_rate` | 0.0–1.0 |
| `can_ids` | Extended IDs to target; empty = all |
| `window_ms` | How long the drop predicate is active |
| `min_frames_received` / `max_drop_ratio` | Pass criteria |

## bus_off

Pumps error frames (or forces bus-off), then recovers and asserts we came back online inside `max_recovery_ms`.

Useful as a smoke test for CanIf status handling without needing a real transceiver.

## j1939_tp_retransmit

Sends a multi-frame J1939 payload with CMDT-style RTS/CTS/ACK. The injector drops a few control frames on purpose so the TP layer has to retry.

Pass if delivery succeeds and at least one retry was observed (and retries stay under the configured max).

## Adding a scenario

1. Drop a new YAML in `config/scenarios/<name>.yaml`
2. Add a branch in `FaultInjector.apply` (or reuse an existing fault type)
3. Append the name under `scenarios:` in `harness.yaml`
4. Cover it with a unit test in `tests/unit/test_bus_and_fault.py`

Keep scenarios short — the orchestrator also enforces `thresholds.scenario_timeout_sec`.
