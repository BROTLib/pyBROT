import logging
from datetime import datetime

import httpx

from .source import WeatherReading, WeatherSource

log = logging.getLogger(__name__)

_SENSOR_CODES = {"temp": "temperature", "humid": "humidity", "press": "pressure"}


class PyobsWeatherSource(WeatherSource):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient()

    async def read(self) -> WeatherReading | None:
        try:
            response = await self._client.get(f"{self.base_url}/api/current/")
            response.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Could not fetch current weather from %s: %s", self.base_url, e)
            return None

        data = response.json()
        sensors = data.get("sensors", {})

        reading = WeatherReading()
        for code, field in _SENSOR_CODES.items():
            sensor = sensors.get(code)
            if sensor is None or sensor.get("good") is False:
                continue
            value = sensor.get("value")
            if value is not None:
                setattr(reading, field, float(value))

        time = data.get("time")
        if time is not None:
            reading.time = datetime.fromisoformat(time)

        return reading


__all__ = ["PyobsWeatherSource"]
