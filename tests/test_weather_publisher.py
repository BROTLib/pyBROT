import asyncio
from datetime import datetime, timedelta, timezone

from pybrotlib.weather import WeatherPublisher, WeatherReading, WeatherSource


class _FakeTransport:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, topic: str, message: str) -> None:
        self.published.append((topic, message))


class _FakeSource(WeatherSource):
    def __init__(self, reading: WeatherReading | None) -> None:
        self.reading = reading

    async def read(self) -> WeatherReading | None:
        return self.reading


def _publisher(
    reading: WeatherReading | None,
    transport: _FakeTransport,
    max_age: float | None = 300.0,
) -> WeatherPublisher:
    return WeatherPublisher(transport, "brot", _FakeSource(reading), max_age=max_age)


async def test_good_reading_publishes_all_three_fields() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(temperature=12.5, humidity=55.0, pressure=1013.2)

    await _publisher(reading, transport)._publish_once()

    assert transport.published == [
        ("brot/Telescope/SET", "command temperature=12.5"),
        ("brot/Telescope/SET", "command humidity=55.0"),
        ("brot/Telescope/SET", "command pressure=1013.2"),
    ]


async def test_none_reading_publishes_nothing() -> None:
    transport = _FakeTransport()

    await _publisher(None, transport)._publish_once()

    assert transport.published == []


async def test_partial_reading_publishes_only_available_fields() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(temperature=12.5, humidity=None, pressure=1013.2)

    await _publisher(reading, transport)._publish_once()

    assert transport.published == [
        ("brot/Telescope/SET", "command temperature=12.5"),
        ("brot/Telescope/SET", "command pressure=1013.2"),
    ]


async def test_stale_reading_publishes_nothing() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(
        temperature=12.5, time=datetime.now(timezone.utc) - timedelta(hours=1)
    )

    await _publisher(reading, transport, max_age=300.0)._publish_once()

    assert transport.published == []


async def test_fresh_reading_within_max_age_publishes() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(
        temperature=12.5, time=datetime.now(timezone.utc) - timedelta(seconds=10)
    )

    await _publisher(reading, transport, max_age=300.0)._publish_once()

    assert transport.published == [("brot/Telescope/SET", "command temperature=12.5")]


async def test_naive_timestamp_is_treated_as_utc() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(
        temperature=12.5,
        time=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
    )

    await _publisher(reading, transport, max_age=300.0)._publish_once()

    assert transport.published == []


async def test_no_max_age_never_treats_reading_as_stale() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(
        temperature=12.5, time=datetime.now(timezone.utc) - timedelta(days=30)
    )

    await _publisher(reading, transport, max_age=None)._publish_once()

    assert transport.published == [("brot/Telescope/SET", "command temperature=12.5")]


async def test_run_publishes_on_interval_until_closed() -> None:
    transport = _FakeTransport()
    reading = WeatherReading(temperature=1.0)
    publisher = WeatherPublisher(transport, "brot", _FakeSource(reading), interval=0.01)

    task = asyncio.create_task(publisher.run())
    for _ in range(1000):
        if len(transport.published) >= 2:
            break
        await asyncio.sleep(0.005)

    await publisher.close()
    await asyncio.wait_for(task, timeout=1)
    assert len(transport.published) >= 2
