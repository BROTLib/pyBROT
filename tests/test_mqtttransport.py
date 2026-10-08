from dataclasses import dataclass

import pytest
from aiomqtt import Message

from pybrotlib.transport.mqtttransport import MQTTTransport


def make_transport() -> MQTTTransport:
    return MQTTTransport(host="localhost", port=1883)


def make_message(topic: str, payload: str) -> Message:
    return Message(
        topic=topic,
        payload=payload.encode("utf-8"),
        qos=0,
        retain=False,
        mid=0,
        properties=None,
    )


async def test_float_field_parsed() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", "0 TELESCOPE.READY_STATE=1.0")
    await transport._process_message(msg)
    assert transport.telemetry.TELESCOPE.READY_STATE == 1.0


async def test_float_field_with_influx_int_suffix() -> None:
    # regression test: '100i' used to crash float() for a field typed float, since only
    # the int branch stripped the InfluxDB line-protocol integer suffix.
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", "0 TELESCOPE.READY_STATE=1i")
    await transport._process_message(msg)
    assert transport.telemetry.TELESCOPE.READY_STATE == 1.0


async def test_int_field_with_influx_suffix() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", "0 TELESCOPE.CONFIG.CAPABILITIES=5i")
    await transport._process_message(msg)
    assert transport.telemetry.TELESCOPE.CONFIG.CAPABILITIES == 5


async def test_string_field_strips_quotes() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", '0 TELESCOPE.INFO.NAME="MyScope"')
    await transport._process_message(msg)
    assert transport.telemetry.TELESCOPE.INFO.NAME == "MyScope"


@pytest.mark.parametrize("name", ["My Scope", "a=b", "x y=z"])
async def test_string_field_with_space_or_equals(name: str) -> None:
    # regression test: split(" ")/split("=") used to truncate or reject such values.
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", f'0 TELESCOPE.INFO.NAME="{name}"')
    await transport._process_message(msg)
    assert transport.telemetry.TELESCOPE.INFO.NAME == name


async def test_bool_field_parsed() -> None:
    @dataclass
    class FakeTelemetry:
        FLAG: bool = False

    transport = make_transport()
    fake = FakeTelemetry()
    transport.telemetry = fake  # type: ignore[assignment]
    msg = make_message("brot/Telescope/Telemetry", "0 FLAG=true")
    await transport._process_message(msg)
    assert fake.FLAG is True


async def test_indexed_sensor_field() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", '0 AUXILIARY.SENSOR[2].NAME="Ambient"')
    await transport._process_message(msg)
    assert transport.telemetry.AUXILIARY.SENSOR[2].NAME == "Ambient"


async def test_unknown_path_is_ignored() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", "0 TELESCOPE.DOES_NOT_EXIST=1.0")
    await transport._process_message(msg)  # must not raise


@pytest.mark.parametrize("payload", ["", "foo", "0", "0 NOEQUALS", "0 =1"])
async def test_malformed_telemetry_is_ignored(payload: str, caplog: pytest.LogCaptureFixture) -> None:
    # regression test: a payload without a field used to raise IndexError and kill run().
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", payload)
    await transport._process_message(msg)  # must not raise
    assert "Malformed telemetry" in caplog.text
    assert transport.data == {}


async def test_non_bytes_payload_is_ignored() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", "0 TELESCOPE.READY_STATE=1.0")
    msg.payload = "not bytes"  # type: ignore[assignment]
    await transport._process_message(msg)  # must not raise, and must not touch telemetry
    assert transport.telemetry.TELESCOPE.READY_STATE == 0.0


async def test_log_topic_does_not_raise() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Log", '0 level="info" message="hello"')
    await transport._process_message(msg)


@pytest.mark.parametrize("value", ["100i", "3", "42i"])
async def test_int_suffix_variants(value: str) -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", f"0 TELESCOPE.CONFIG.CAPABILITIES={value}")
    await transport._process_message(msg)
    assert transport.telemetry.TELESCOPE.CONFIG.CAPABILITIES == int(value.removesuffix("i"))


TS = "1791449700123456700"


@pytest.mark.parametrize("suffix", ["", f" {TS}"])
async def test_bool_field_with_optional_timestamp(suffix: str) -> None:
    # regression test: "true <ts>" used to read as False.
    @dataclass
    class FakeTelemetry:
        FLAG: bool = False

    transport = make_transport()
    fake = FakeTelemetry()
    transport.telemetry = fake  # type: ignore[assignment]
    await transport._process_message(make_message("brot/Telescope/Telemetry", f"0 FLAG=true{suffix}"))
    assert fake.FLAG is True
    assert transport.data["FLAG"] == "true"


@pytest.mark.parametrize("suffix", ["", f" {TS}"])
async def test_numeric_fields_with_optional_timestamp(suffix: str) -> None:
    transport = make_transport()
    await transport._process_message(make_message("brot/Telescope/Telemetry", f"0 TELESCOPE.READY_STATE=1.5{suffix}"))
    await transport._process_message(
        make_message("brot/Telescope/Telemetry", f"0 TELESCOPE.CONFIG.CAPABILITIES=5i{suffix}")
    )
    assert transport.telemetry.TELESCOPE.READY_STATE == 1.5
    assert transport.telemetry.TELESCOPE.CONFIG.CAPABILITIES == 5


@pytest.mark.parametrize("name", ["MyScope", "My Scope", "a=b", "x y=z", 'say \\"hi\\" now'])
@pytest.mark.parametrize("suffix", ["", f" {TS}"])
async def test_string_field_with_optional_timestamp(name: str, suffix: str) -> None:
    transport = make_transport()
    await transport._process_message(
        make_message("brot/Telescope/Telemetry", f'0 TELESCOPE.INFO.NAME="{name}"{suffix}')
    )
    assert transport.telemetry.TELESCOPE.INFO.NAME == name
    assert transport.data["TELESCOPE.INFO.NAME"] == f'"{name}"'


@pytest.mark.parametrize("key", ["POSITION.EQUATORIAL.RA_ICRS", "POSITION.EQUATORIAL.RA_J2000", "OBJECT.EQUATORIAL.RA"])
async def test_ra_converted_from_hours(key: str) -> None:
    transport = MQTTTransport(host="localhost", port=1883, ra_in_hours=True)
    await transport._process_message(make_message("brot/Telescope/Telemetry", f"0 {key}=2.0"))
    obj = transport.telemetry
    for token in key.split("."):
        obj = getattr(obj, token)
    assert obj == 30.0


async def test_ra_not_converted_by_default() -> None:
    transport = make_transport()
    await transport._process_message(make_message("brot/Telescope/Telemetry", "0 POSITION.EQUATORIAL.RA_ICRS=30.0"))
    assert transport.telemetry.POSITION.EQUATORIAL.RA_ICRS == 30.0


async def test_dec_and_instrumental_ra_never_converted() -> None:
    transport = MQTTTransport(host="localhost", port=1883, ra_in_hours=True)
    await transport._process_message(make_message("brot/Telescope/Telemetry", "0 POSITION.EQUATORIAL.DEC_ICRS=20.0"))
    await transport._process_message(make_message("brot/Telescope/Telemetry", "0 OBJECT.INSTRUMENTAL.RA=40.0"))
    assert transport.telemetry.POSITION.EQUATORIAL.DEC_ICRS == 20.0
    assert transport.telemetry.OBJECT.INSTRUMENTAL.RA == 40.0


async def test_apparent_fields_parsed() -> None:
    transport = make_transport()
    await transport._process_message(make_message("brot/Telescope/Telemetry", "0 POSITION.EQUATORIAL.HA_APPARENT=1.5"))
    assert transport.telemetry.POSITION.EQUATORIAL.HA_APPARENT == 1.5


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, int]] = []

    async def publish(self, topic: str, payload: bytes, qos: int = 0) -> None:
        self.calls.append((topic, payload, qos))


def make_connected_transport() -> tuple[MQTTTransport, _RecordingClient]:
    transport = make_transport()
    client = _RecordingClient()
    transport._client = client  # type: ignore[assignment]
    transport._connected_event.set()
    return transport, client


async def test_publish_defaults_to_qos_1() -> None:
    transport, client = make_connected_transport()
    await transport.publish("brot/Telescope/SET", "command stop=true")
    assert client.calls == [("brot/Telescope/SET", b"command stop=true", 1)]


async def test_publish_qos_can_be_overridden() -> None:
    transport, client = make_connected_transport()
    await transport.publish("brot/Telescope/SET", "x", qos=0)
    assert client.calls[0][2] == 0


async def test_publish_times_out_when_not_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pybrotlib.transport.mqtttransport._PUBLISH_TIMEOUT", 0.01)
    transport = make_transport()
    with pytest.raises(TimeoutError):
        await transport.publish("brot/Telescope/SET", "x")
