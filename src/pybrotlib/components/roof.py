from enum import Enum

from ..components.base import BROTBase


class RoofStatus(Enum):
    CLOSED = "closed"
    OPEN = "open"
    OPENING = "opening"
    CLOSING = "closing"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class BROTRoof(BROTBase):
    @property
    def in_motion(self) -> bool:
        return (self._telemetry.AUXILIARY.DOME.REALPOS == 0.5) or (
            self._telemetry.AUXILIARY.DOME.MOTION_STATE == 1.0
        )

    @property
    def status(self) -> RoofStatus:
        match self._telemetry.AUXILIARY.DOME.READY_STATE:
            case 0.0:
                return RoofStatus.CLOSED
            case 0.3:
                return RoofStatus.CLOSING
            case 0.5:
                return RoofStatus.STOPPED
            case 0.7:
                return RoofStatus.OPENING
            case -1.0:
                return RoofStatus.ERROR
            case _:
                return RoofStatus.UNKNOWN

    @property
    def error_state(self) -> bool:
        return self._telemetry.AUXILIARY.DOME.ERROR_STATE != 0

    async def open(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_open=1"
        )

    async def close(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_close=1"
        )

    async def reset(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_reset=1"
        )


__all__ = ["BROTRoof", "RoofStatus"]
