import pytest

from pybrotlib.components import BROTTelescope
from pybrotlib.transport import Transport


class _FakeTransport(Transport):
    def __init__(self, multi_field_commands: bool) -> None:
        super().__init__(multi_field_commands=multi_field_commands)
        self.published: list[tuple[str, str]] = []

    async def publish(self, topic: str, message: str, qos: int = 1) -> None:
        self.published.append((topic, message))


async def test_track_sends_three_messages_by_default() -> None:
    transport = _FakeTransport(multi_field_commands=False)
    await BROTTelescope(transport, "brot").track(10.5, -20.25)
    assert transport.published == [
        ("brot/Telescope/SET", "command rightascension=10.5"),
        ("brot/Telescope/SET", "command declination=-20.25"),
        ("brot/Telescope/SET", "command track=1"),
    ]


async def test_move_sends_three_messages_by_default() -> None:
    transport = _FakeTransport(multi_field_commands=False)
    await BROTTelescope(transport, "brot").move(45.0, 180.0)
    assert transport.published == [
        ("brot/Telescope/SET", "command elevation=45.0"),
        ("brot/Telescope/SET", "command azimuth=180.0"),
        ("brot/Telescope/SET", "command slew=1"),
    ]


async def test_track_sends_one_message_with_multi_field_commands() -> None:
    transport = _FakeTransport(multi_field_commands=True)
    await BROTTelescope(transport, "brot").track(10.5, -20.25)
    assert transport.published == [("brot/Telescope/SET", "command rightascension=10.5,declination=-20.25,track=1")]


async def test_move_sends_one_message_with_multi_field_commands() -> None:
    transport = _FakeTransport(multi_field_commands=True)
    await BROTTelescope(transport, "brot").move(45.0, 180.0)
    assert transport.published == [("brot/Telescope/SET", "command elevation=45.0,azimuth=180.0,slew=1")]


@pytest.mark.parametrize("flag", [False, True])
def test_mqtt_transport_passes_flag(flag: bool) -> None:
    from pybrotlib.transport import MQTTTransport

    assert MQTTTransport("localhost", 1883, multi_field_commands=flag).multi_field_commands is flag
