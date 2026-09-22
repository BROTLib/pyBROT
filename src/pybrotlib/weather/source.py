from dataclasses import dataclass
from datetime import datetime


@dataclass
class WeatherReading:
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    time: datetime | None = None


class WeatherSource:
    async def read(self) -> WeatherReading | None:
        raise NotImplementedError


__all__ = ["WeatherReading", "WeatherSource"]
