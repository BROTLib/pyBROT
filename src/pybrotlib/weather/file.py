import json
import logging
from datetime import datetime
from pathlib import Path

import yaml

from .source import WeatherReading, WeatherSource

log = logging.getLogger(__name__)


class FileWeatherSource(WeatherSource):
    def __init__(self, path: str | Path):
        self.path = Path(path)

    async def read(self) -> WeatherReading | None:
        try:
            text = self.path.read_text()
        except OSError as e:
            log.warning("Could not read weather file %s: %s", self.path, e)
            return None

        try:
            if self.path.suffix in (".yml", ".yaml"):
                data = yaml.safe_load(text)
            else:
                data = json.loads(text)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            log.warning("Could not parse weather file %s: %s", self.path, e)
            return None

        time = data.get("time")
        return WeatherReading(
            temperature=data.get("temperature"),
            humidity=data.get("humidity"),
            pressure=data.get("pressure"),
            time=datetime.fromisoformat(time) if time is not None else None,
        )


__all__ = ["FileWeatherSource"]
