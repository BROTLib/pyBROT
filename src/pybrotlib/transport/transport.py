import asyncio
import time
from typing import Any

from ..telemetry import Telemetry


class Transport:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.telemetry = Telemetry()
        self._connected = False
        self._closing = asyncio.Event()
        self._last_message_at: float | None = None

    async def close(self) -> None:
        self._closing.set()

    async def run(self) -> None:
        pass

    async def publish(self, topic: str, message: str) -> None:
        pass

    @property
    def connected(self) -> bool:
        return self._connected

    def telemetry_age(self) -> float | None:
        """Seconds since the last message was received, or None if none ever was."""
        if self._last_message_at is None:
            return None
        return time.monotonic() - self._last_message_at
