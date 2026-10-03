# CANoe / CAPL samples

Optional. Linux CI does not use these files.

| File | Purpose |
|------|---------|
| `FaultInjection.can` | CAPL hooks for frame drop / bus-off / TP.CM drop |

Wire the CAPL into your Vector CANoe configuration, set `backend: canoe` in `config/harness.yaml`, and run on a Windows agent with `pywin32`.

Full notes: [docs/canoe.md](../docs/canoe.md).
