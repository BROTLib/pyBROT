import httpx

from pybrotlib.weather import PyobsWeatherSource


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_good_reading_populates_all_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/current/"
        return httpx.Response(
            200,
            json={
                "time": "2026-09-22T10:00:00Z",
                "good": True,
                "sensors": {
                    "temp": {"good": True, "value": 12.5},
                    "humid": {"good": True, "value": 55.0},
                    "press": {"good": True, "value": 1013.2},
                },
            },
        )

    source = PyobsWeatherSource("https://weather.example.org", client=_client(handler))
    reading = await source.read()

    assert reading is not None
    assert reading.temperature == 12.5
    assert reading.humidity == 55.0
    assert reading.pressure == 1013.2
    assert reading.time is not None


async def test_bad_sensor_is_left_none_others_still_populate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "time": "2026-09-22T10:00:00Z",
                "good": False,
                "sensors": {
                    "temp": {"good": True, "value": 12.5},
                    "humid": {"good": False, "value": 200.0},
                    "press": {"good": True, "value": 1013.2},
                },
            },
        )

    source = PyobsWeatherSource("https://weather.example.org", client=_client(handler))
    reading = await source.read()

    assert reading is not None
    assert reading.temperature == 12.5
    assert reading.humidity is None
    assert reading.pressure == 1013.2


async def test_missing_sensor_value_is_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "time": "2026-09-22T10:00:00Z",
                "good": True,
                "sensors": {
                    "temp": {"good": None, "value": None},
                    "humid": {"good": True, "value": 55.0},
                    "press": {"good": True, "value": 1013.2},
                },
            },
        )

    source = PyobsWeatherSource("https://weather.example.org", client=_client(handler))
    reading = await source.read()

    assert reading is not None
    assert reading.temperature is None
    assert reading.humidity == 55.0


async def test_http_error_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    source = PyobsWeatherSource("https://weather.example.org", client=_client(handler))
    reading = await source.read()

    assert reading is None


async def test_network_error_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    source = PyobsWeatherSource("https://weather.example.org", client=_client(handler))
    reading = await source.read()

    assert reading is None
