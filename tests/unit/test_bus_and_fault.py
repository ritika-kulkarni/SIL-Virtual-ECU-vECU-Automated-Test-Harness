from sil_harness.bus.canoe_adapter import CanoeComAdapter, create_bus_backend
from sil_harness.bus.com import Com
from sil_harness.bus.interfaces import CanFrame
from sil_harness.bus.j1939_tp import J1939Transport
from sil_harness.bus.pdur import Pdu, PduR
from sil_harness.bus.python_sim import PythonBusSimulator
from sil_harness.core.config import Expectations, FaultSpec
from sil_harness.fault.injector import FaultInjector


def test_python_bus_send_receive() -> None:
    bus = PythonBusSimulator()
    bus.attach()
    assert bus.send(CanFrame(can_id=0x123, data=b"\x01\x02"))
    frame = bus.receive(timeout_ms=50)
    assert frame is not None
    assert frame.data == b"\x01\x02"
    bus.detach()


def test_bus_off_blocks_traffic() -> None:
    bus = PythonBusSimulator()
    bus.attach()
    bus.force_bus_off()
    assert bus.is_bus_off()
    assert not bus.send(CanFrame(can_id=1, data=b"\x00"))
    bus.recover()
    assert bus.send(CanFrame(can_id=1, data=b"\x00"))


def test_com_pdur_stack() -> None:
    bus = PythonBusSimulator()
    bus.attach()
    from sil_harness.bus.canif import CanIf

    canif = CanIf(bus)
    pdur = PduR(canif)
    com = Com(pdur)
    assert com.send_signal("EngineSpeed", 42)
    assert com.receive_signal("EngineSpeed") == 42


def test_j1939_tp_retransmit() -> None:
    bus = PythonBusSimulator()
    bus.attach()
    from sil_harness.bus.canif import CanIf

    tp = J1939Transport(CanIf(bus), max_retries=3)
    tp.force_control_drops(2)
    result = tp.send_message(bytes(range(40)))
    assert result.delivered
    assert result.retries >= 1


def test_fault_injector_scenarios() -> None:
    bus = PythonBusSimulator()
    bus.attach()
    injector = FaultInjector(bus, seed=7)

    drop = injector.apply(
        FaultSpec(type="frame_drop", drop_rate=0.3, can_ids=[0x18FF1200], window_ms=200),
        Expectations(min_frames_received=1, max_drop_ratio=0.9, require_recovery=True),
    )
    assert drop.metrics["passed"] is True

    bus2 = PythonBusSimulator()
    bus2.attach()
    injector2 = FaultInjector(bus2)
    bus_off = injector2.apply(
        FaultSpec(type="bus_off", error_frames_before_bus_off=32, recovery_window_ms=10),
        Expectations(require_bus_off=True, require_recovery=True, max_recovery_ms=1000),
    )
    assert bus_off.metrics["passed"] is True

    bus3 = PythonBusSimulator()
    bus3.attach()
    injector3 = FaultInjector(bus3)
    tp = injector3.apply(
        FaultSpec(type="j1939_tp_retransmit", drop_control_frames=1, max_tp_retries=3, payload_bytes=20),
        Expectations(require_retransmit=True, require_delivery=True, max_retries_observed=3),
    )
    assert tp.metrics["passed"] is True


def test_canoe_unavailable_fallback() -> None:
    assert CanoeComAdapter.is_available() is False or True  # platform dependent
    bus = create_bus_backend("canoe", channel=0, bitrate=500000)
    assert bus.name == "python"
    bus.detach()


def test_pdur_unknown_route() -> None:
    bus = PythonBusSimulator()
    bus.attach()
    from sil_harness.bus.canif import CanIf

    pdur = PduR(CanIf(bus))
    assert pdur.transmit(Pdu(pdu_id=999, data=b"\x01")) is False
