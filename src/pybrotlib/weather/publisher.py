import asyncio
import logging
from datetime import datetime, timezone

from ..transport import Transport
from .source import WeatherReading, WeatherSource

log = logging.getLogger(__name__)

_FIELDS = ("temperature", "humidity", "pressure")


class WeatherPublisher:
    def __init__(
        self,
        transport: Transport,
        site: str,
        source: WeatherSource,
        interval: float = 60.0,
        max_age: float | None = 300.0,
    ):
        self.transport = transport
        self.site = site
        self.source = source
        self.interval = interval
        self.max_age = max_age
        self._closing = asyncio.Event()

    async def close(self) -> None:
        self._closing.set()

    async def run(self) -> None:
        while not self._closing.is_set():
            try:
                await asyncio.wait_for(self._closing.wait(), timeout=self.interval)
                return
            except TimeoutError:
                pass
            await self._publish_once()

    async def _publish_once(self) -> None:
        reading = await self.source.read()
        if reading is None:
            log.debug("No weather reading available from %s.", self.source)
            return

        if self._is_stale(reading):
            log.warning(
                "Weather reading from %s is stale (time=%s), not publishing.",
                self.source,
                reading.time,
            )
            return

        for field in _FIELDS:
            value = getattr(reading, field)
            if value is not None:
                await self.transport.publish(
                    f"{self.site}/Telescope/SET", f"command {field}={value}"
                )

    def _is_stale(self, reading: WeatherReading) -> bool:
        if self.max_age is None or reading.time is None:
            return False
        # a naive timestamp (e.g. from a hand-written weather file) is assumed to already be UTC
        time = (
            reading.time
            if reading.time.tzinfo is not None
            else reading.time.replace(tzinfo=timezone.utc)
        )
        age = (datetime.now(timezone.utc) - time).total_seconds()
        return age > self.max_age


__all__ = ["WeatherPublisher"]
