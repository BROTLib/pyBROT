import asyncio
from typing import Any

from ..telemetry import Telemetry


class Transport:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.telemetry = Telemetry()
        self._connected = False
        self._closing = asyncio.Event()

    async def close(self) -> None:
        self._closing.set()

    async def run(self) -> None:
        pass

    async def publish(self, topic: str, message: str) -> None:
        pass

    @property
    def connected(self) -> bool:
        return self._connected
