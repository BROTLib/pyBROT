import asyncio
import time

from ..telemetry import Telemetry


class Transport:
    def __init__(self, ra_in_hours: bool = False) -> None:
        # Legacy PLCs publish RA telemetry in hours, newer ones in degrees (BROTLib#37). Set True for
        # legacy PLCs: RA fields are then multiplied by 15 on receipt, so Telemetry always holds degrees.
        self.ra_in_hours = ra_in_hours
        self.data: dict[str, str] = {}
        self.telemetry = Telemetry()
        self._connected = False
        # PLC presence from the retained {site}/Telemetry/status last-will topic; None = unknown
        # (no status message seen yet, broker connection down, or PLC without last-will support)
        self.plc_online: bool | None = None
        self._closing = asyncio.Event()
        self._last_message_at: float | None = None

    async def close(self) -> None:
        self._closing.set()

    async def run(self) -> None:
        pass

    async def publish(self, topic: str, message: str, qos: int = 1) -> None:
        pass

    @property
    def connected(self) -> bool:
        return self._connected

    def telemetry_age(self) -> float | None:
        """Seconds since the last message was received, or None if none ever was."""
        if self._last_message_at is None:
            return None
        return time.monotonic() - self._last_message_at
