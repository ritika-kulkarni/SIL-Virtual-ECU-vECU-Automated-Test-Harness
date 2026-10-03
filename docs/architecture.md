# Architecture

This harness exists so teams can run CAN/J1939 regression without waiting on a HIL rack. Jenkins starts a Docker agent, builds a stub vECU, Python (or CANoe) drives the bus, faults get injected, and results land in Artifactory with coverage.

## System overview

```mermaid
flowchart TB
  subgraph ci [CI_entry]
    PR[PullRequest]
    Jenkins[Jenkinsfile]
    Agent[DockerCIAgent]
  end

  subgraph runtime [SIL_runtime]
    Orch[Orchestrator]
    Bus[BusBackend]
    Fault[FaultInjector]
    Bridge[VecuBridge]
    VecuProc[vecu_sim]
  end

  subgraph stack [BSW_and_app]
    CanIf[CanIf]
    PduR[PduR]
    Com[Com]
    App[J1939App]
  end

  subgraph out [Outputs]
    Html[HtmlReport]
    Cov[gcov_coverage]
    Art[Artifactory]
  end

  PR --> Jenkins --> Agent
  Agent --> Orch
  Orch --> Bus
  Orch --> Fault
  Orch --> Bridge --> VecuProc
  Bus --> CanIf --> PduR --> Com --> App
  Fault --> Bus
  Orch --> Html --> Art
  Orch --> Cov --> Art
```

## End-to-end sequence

What happens when you run `sil-harness run` (same path Jenkins uses):

```mermaid
sequenceDiagram
  participant CLI as sil_harness_CLI
  participant Orch as Orchestrator
  participant Runner as VecuRunner
  participant Bus as BusBackend
  participant Fault as FaultInjector
  participant Rep as Reporter

  CLI->>Orch: run_config_and_scenarios
  Orch->>Runner: build_and_gtest
  Runner-->>Orch: binary_ready
  Orch->>Runner: start_TCP_bridge
  Runner-->>Orch: PONG
  Orch->>Bus: attach_python_or_canoe
  loop each_scenario
    Orch->>Fault: apply_fault_and_check
    Fault->>Bus: TX_RX_inject
    Fault-->>Orch: FaultResult
  end
  Orch->>Bus: detach
  Orch->>Rep: html_plus_coverage
  Orch->>Rep: evaluate_gates
  Orch-->>CLI: exit_0_1_or_2
```

## Component map

```mermaid
flowchart LR
  subgraph pythonPkg [src_sil_harness]
    cli[cli]
    core[core]
    bus[bus]
    fault[fault]
    vecuPy[vecu]
    pipe[pipeline]
    report[reporting]
  end

  cli --> pipe
  pipe --> bus
  pipe --> fault
  pipe --> vecuPy
  pipe --> report
  fault --> bus
  bus --> core
  report --> core
  vecuPy --> core
```

| Package | What it owns |
|---------|----------------|
| `core/` | YAML config models, logging, retries, exception types |
| `bus/` | `BusBackend` protocol, Python sim, CANoe COM adapter, COM/PduR/CanIf/J1939 TP |
| `fault/` | Scenario fault application + pass/fail metrics |
| `vecu/` | CMake build, process lifecycle, TCP bridge |
| `pipeline/` | Orchestrator: load → run → report → gate → publish |
| `reporting/` | HTML report, gcov/lcov helpers, Artifactory clients |
| `cli.py` | `run` / `report` / `publish` entrypoints |

## Bus backend choice

```mermaid
flowchart TD
  Start[create_bus_backend]
  Start -->|backend_python| Py[PythonBusSimulator]
  Start -->|backend_canoe| Try[Try_CANoe_COM]
  Try -->|win32_and_pywin32_ok| Canoe[CanoeComAdapter]
  Try -->|missing_or_attach_fail| Fallback[Fall_back_to_Python]
  Fallback --> Py
```

Linux CI always ends up on the Python simulator. Windows/WSL agents with Vector CANoe can set `backend: canoe` in `config/harness.yaml`.

## AUTOSAR-ish data path

Same layering on both sides: Python wrappers for SIL injection, and the C stub under `vecu/` for coverage.

```mermaid
flowchart BT
  App[J1939App_signals_TP]
  Com[Com_pack_unpack]
  PduR[PduR_route_table]
  CanIf[CanIf_TX_RX]
  Bus[CAN_bus_backend]

  App --> Com --> PduR --> CanIf --> Bus
  Bus --> CanIf --> PduR --> Com --> App
```

Default routing table (PDU ID → CAN ID):

| PDU ID | CAN ID | Use |
|--------|--------|-----|
| 1 | `0x18EAFF00` | Request |
| 2 | `0x18ECFF00` | TP.CM |
| 3 | `0x18EBFF00` | TP.DT |
| 4 | `0x18FF1200` | App PDU |

## Stub vECU process

```mermaid
flowchart LR
  Orch[Orchestrator]
  Bridge[VecuBridge_TCP]
  Main[vecu_sim_main]
  Lib[vecu_bsw_lib]

  Orch -->|PING_SIGNAL_TP_BUSOFF| Bridge
  Bridge -->|127.0.0.1:19000| Main
  Main --> Lib
  Lib --> CanIfC[CanIf.c]
  Lib --> PduRC[PduR.c]
  Lib --> ComC[Com.c]
  Lib --> J1939C[J1939App.c]
```

`main.c` is only the control plane. Business logic stays in the static library so GTest can link the same objects the sim uses.

## Fault injection

```mermaid
flowchart TD
  YAML[scenario_YAML]
  Inj[FaultInjector]
  YAML --> Inj
  Inj -->|frame_drop| Drop[drop_predicate_on_IDs]
  Inj -->|bus_off| Off[error_frames_then_recover]
  Inj -->|j1939_tp_retransmit| TP[drop_RTS_CTS_ACK]
  Drop --> Result[FaultResult_metrics]
  Off --> Result
  TP --> Result
```

Details and YAML fields: [scenarios.md](scenarios.md).

## Reporting and publish

```mermaid
flowchart LR
  Orch[Orchestrator]
  Html[sil_report.html]
  Sum[summary.json]
  Cov[coverage_dir]
  Client[ArtifactoryClient]

  Orch --> Html
  Orch --> Sum
  Orch --> Cov
  Html --> Client
  Sum --> Client
  Cov --> Client
  Client -->|mode_mock| FS[artifacts_artifactory]
  Client -->|mode_http| HTTP[Artifactory_PUT]
```

Quality gates (pass rate, line/branch coverage) are read from `config/harness.yaml` → `thresholds`. Exit code `2` means a gate failed; `1` means one or more scenarios failed.

## Design choices that matter day-to-day

- **Swappable bus** — keep Linux green without a CANoe license; Windows can still attach COM when available.
- **Separate C binary** — coverage and GTest stay close to real ECU build habits; Python does not get linked into the “ECU”.
- **YAML scenarios** — fault knobs live next to the PR checklist, not buried in code.
- **Mock Artifactory** — laptop runs produce the same artifact layout CI would upload.
