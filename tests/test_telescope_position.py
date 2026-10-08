from aiomqtt import Message

from pybrotlib.brot import BROT
from pybrotlib.transport import MQTTTransport


def _msg(payload: str) -> Message:
    return Message(
        topic="brot/Telescope/Telemetry", payload=payload.encode(), qos=0, retain=False, mid=0, properties=None
    )


async def _brot(*lines: str) -> BROT:
    transport = MQTTTransport(host="localhost", port=1883)
    for line in lines:
        await transport._process_message(_msg(line))
    return BROT(transport, "brot")


async def test_position_from_icrs() -> None:
    brot = await _brot("0 POSITION.EQUATORIAL.RA_ICRS=1.5", "0 POSITION.EQUATORIAL.DEC_ICRS=-20.0")
    assert brot.telescope.right_ascension == 22.5
    assert brot.telescope.declination == -20.0


async def test_position_falls_back_to_j2000() -> None:
    # e.g. MONETN only publishes *_J2000 (RA in hours here, converted to degrees)
    brot = await _brot("0 POSITION.EQUATORIAL.RA_J2000=2.5", "0 POSITION.EQUATORIAL.DEC_J2000=30.0")
    assert brot.telescope.right_ascension == 37.5
    assert brot.telescope.declination == 30.0


async def test_position_prefers_icrs_when_both_published() -> None:
    brot = await _brot("0 POSITION.EQUATORIAL.RA_J2000=2.5", "0 POSITION.EQUATORIAL.RA_ICRS=1.5")
    assert brot.telescope.right_ascension == 22.5
