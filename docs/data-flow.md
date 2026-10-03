# Data flow

How frames, commands, and artifacts move through a single `sil-harness run`.

## Frame path during a scenario

```mermaid
sequenceDiagram
  participant Inj as FaultInjector
  participant Com as Com_Py
  participant PduR as PduR_Py
  participant CanIf as CanIf_Py
  participant Bus as PythonBusSimulator

  Inj->>Com: send_signal_or_raw
  Com->>PduR: Pdu
  PduR->>CanIf: can_id_plus_payload
  CanIf->>Bus: send_CanFrame
  Note over Bus: drop_predicate_may_discard
  Bus-->>CanIf: queue_or_drop
  CanIf-->>PduR: receive_loopback
  PduR-->>Com: indicate_Pdu
```

## vECU control-plane commands

The orchestrator talks to `vecu_sim` over TCP (default `127.0.0.1:19000`).

| Command | Response | Purpose |
|---------|----------|---------|
| `PING` | `PONG` | readiness check |
| `SIGNAL <name> <value>` | `OK` / `ERR` | exercise Com TX |
| `TP <len>` | `OK delivered=…` | multi-frame J1939 send |
| `BUSOFF` / `RECOVER` | `OK` | force CanIf status |
| `STATUS` | `STATUS ONLINE\|BUS_OFF …` | counters |
| `QUIT` | `BYE` | close session |

```mermaid
sequenceDiagram
  participant Orch as Orchestrator
  participant Br as VecuBridge
  participant Sim as vecu_sim

  Orch->>Br: connect
  Br->>Sim: PING
  Sim-->>Br: PONG
  Orch->>Br: STATUS
  Sim-->>Br: STATUS_ONLINE
  Note over Orch: scenarios_run_on_Python_bus
  Orch->>Br: QUIT
  Sim-->>Br: BYE
```

Today the heavy fault traffic runs on the Python bus stack. The vECU process is still started so startup, IPC, and GTest/coverage stay in the same pipeline you would use with a fuller ECU image later.

## Artifact layout after a run

```
artifacts/
  reports/
    sil_report.html      # human-readable SIL report
    summary.json         # machine-readable + gate flags
  coverage/
    coverage.info        # lcov or synthesized
    index.html           # simple coverage page
  artifactory/           # only when mode=mock
    <branch>/<build>/
      sil_report.html
      summary.json
      coverage/
```

## Config → runtime binding

```mermaid
flowchart LR
  H[harness.yaml]
  S[scenarios_star_yaml]
  H --> Cfg[HarnessConfig]
  S --> Sc[ScenarioConfig_list]
  Cfg --> Orch[Orchestrator]
  Sc --> Orch
  Cfg --> BusCfg[bitrate_SA_DA]
  Cfg --> Gates[thresholds]
  Cfg --> ArtCfg[artifactory_mode]
```
