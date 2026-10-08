import asyncio

import pytest
from aiomqtt import MqttError

from pybrotlib.transport import Transport
from pybrotlib.weather import Dut1Publisher


class _FakeTransport(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.published: list[tuple[str, str]] = []

    async def publish(self, topic: str, message: str, qos: int = 1) -> None:
        self.published.append((topic, message))


async def test_publishes_plausible_dut1() -> None:
    transport = _FakeTransport()
    await Dut1Publisher(transport, "brot")._publish_once()

    assert len(transport.published) == 1
    topic, message = transport.published[0]
    assert topic == "brot/Telescope/SET"
    assert message.startswith("command dut1=")
    # UT1-UTC is kept within +/-0.9 s by leap seconds
    assert abs(float(message.removeprefix("command dut1="))) < 0.9


async def test_nothing_published_when_value_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _FakeTransport()
    publisher = Dut1Publisher(transport, "brot")

    def fail() -> float:
        raise ValueError("outside IERS table")

    monkeypatch.setattr("pybrotlib.weather.dut1.Time.now", fail)
    await publisher._publish_once()

    assert transport.published == []


async def test_run_survives_publish_failure() -> None:
    class _FailingTransport(_FakeTransport):
        async def publish(self, topic: str, message: str, qos: int = 1) -> None:
            raise MqttError("down")

    publisher = Dut1Publisher(_FailingTransport(), "brot", interval=0.01)
    task = asyncio.create_task(publisher.run())
    await asyncio.sleep(0.05)
    assert not task.done()
    await publisher.close()
    await asyncio.wait_for(task, timeout=1)
