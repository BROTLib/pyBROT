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
        return self._telemetry.AUXILIARY.DOME.MOTION_STATE == 1.0

    @property
    def status(self) -> RoofStatus:
        if self._telemetry.AUXILIARY.DOME.REALPOS == 0.0:
            return RoofStatus.CLOSED
        elif self._telemetry.AUXILIARY.DOME.REALPOS == 1.0:
            return RoofStatus.OPEN
        elif self._telemetry.AUXILIARY.DOME.REALPOS == -1.0:
            return RoofStatus.ERROR
        else:
            if self._telemetry.AUXILIARY.DOME.MOTION_STATE == 0.0:
                return RoofStatus.STOPPED
            else:
                if self._telemetry.AUXILIARY.DOME.TARGETPOS == 0.0:
                    return RoofStatus.CLOSING
                else:
                    return RoofStatus.OPENING

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

    async def stop(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_stop=1"
        )

    async def reset(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_reset=1"
        )


__all__ = ["BROTRoof", "RoofStatus"]
