import asyncio

from pybrotlib.transport.transport import Transport


async def test_telemetry_age_none_before_first_message() -> None:
    transport = Transport()
    assert transport.telemetry_age() is None


async def test_telemetry_age_increases_over_time() -> None:
    transport = Transport()
    transport._last_message_at = None
    import time

    transport._last_message_at = time.monotonic()
    age1 = transport.telemetry_age()
    assert age1 is not None
    await asyncio.sleep(0.05)
    age2 = transport.telemetry_age()
    assert age2 is not None
    assert age2 > age1


async def test_telemetry_age_resets_on_new_message() -> None:
    import time

    transport = Transport()
    transport._last_message_at = time.monotonic() - 10.0
    assert transport.telemetry_age() >= 10.0  # type: ignore[operator]

    transport._last_message_at = time.monotonic()
    assert transport.telemetry_age() < 1.0  # type: ignore[operator]
