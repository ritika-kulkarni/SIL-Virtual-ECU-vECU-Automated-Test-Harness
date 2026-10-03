# Architecture

Short version: Jenkins runs a Docker agent, the agent builds a stub vECU, Python drives a virtual CAN bus (or CANoe), faults get injected, then we publish HTML + coverage.

## Pipeline path

```
Pull request
    │
    ▼
Jenkinsfile  ──►  docker/Dockerfile.ci agent
    │
    ├─► pytest (Python unit)
    ├─► cmake / gtest / gcov  (vecu/)
    ├─► sil-harness run       (scenarios)
    ├─► coverage HTML
    └─► Artifactory publish
```

## Python package (`src/sil_harness`)

| Area | Role |
|------|------|
| `core/` | Config (pydantic), logging, retries, error types |
| `bus/` | `BusBackend` protocol, Python simulator, CANoe adapter, COM/PduR/CanIf/J1939 TP |
| `fault/` | Applies scenario faults and checks expectations |
| `vecu/` | Builds/starts the C binary, TCP bridge |
| `pipeline/` | Orchestrator — load scenarios, run, report, gate |
| `reporting/` | HTML report, gcov/lcov helpers, Artifactory client |
| `cli.py` | `sil-harness run \| report \| publish` |

The bus backend is swappable. `create_bus_backend("canoe")` tries COM first; on Linux (or any attach failure) it returns the Python simulator.

## Stub vECU (`vecu/`)

C modules meant to stand in for AUTOSAR BSW during SIL:

- `CanIf` — TX/RX with loopback + bus-off
- `PduR` — static PDU ↔ CAN ID table
- `Com` — signal pack/unpack
- `J1939App` — TP segmentation + a few decision branches for coverage

`main.c` opens a TCP port (default `19000`) so the harness can poke it (`PING`, `SIGNAL`, `TP`, `BUSOFF`, …) without linking Python into the ECU image.

## Reporting

- HTML: `artifacts/reports/sil_report.html`
- JSON summary: `artifacts/reports/summary.json` (includes gate results)
- Coverage: `artifacts/coverage/` (lcov/gcovr when available; otherwise a synthesized summary so CI still has something to publish)

Artifactory:

- `mode: mock` → copy into `artifacts/artifactory/...` (good for laptop runs)
- `mode: http` → PUT to your Artifactory repo with retries
