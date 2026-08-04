from dataclasses import dataclass

import pytest
from aiomqtt import Message

from pybrotlib.transport.mqtttransport import MQTTTransport


def make_transport() -> MQTTTransport:
    return MQTTTransport(host="localhost", port=1883)


def make_message(topic: str, payload: str) -> Message:
    return Message(topic=topic, payload=payload.encode("utf-8"), qos=0, retain=False, mid=0, properties=None)


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


async def test_bool_field_parsed() -> None:
    @dataclass
    class FakeTelemetry:
        FLAG: bool = False

    transport = make_transport()
    transport.telemetry = FakeTelemetry()  # type: ignore[assignment]
    msg = make_message("brot/Telescope/Telemetry", "0 FLAG=true")
    await transport._process_message(msg)
    assert transport.telemetry.FLAG is True


async def test_indexed_sensor_field() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", '0 AUXILIARY.SENSOR[2].NAME="Ambient"')
    await transport._process_message(msg)
    assert transport.telemetry.AUXILIARY.SENSOR[2].NAME == "Ambient"


async def test_unknown_path_is_ignored() -> None:
    transport = make_transport()
    msg = make_message("brot/Telescope/Telemetry", "0 TELESCOPE.DOES_NOT_EXIST=1.0")
    await transport._process_message(msg)  # must not raise


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
