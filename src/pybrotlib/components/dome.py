from enum import Enum

from ..components.base import BROTBase


class DomeShutterStatus(Enum):
    CLOSED = "closed"
    MOVING = "moving"
    OPEN = "open"
    UNKNOWN = "unknown"


class DomeStatus(Enum):
    PARKED = "parked"
    ERROR = "error"
    TRACKING = "tracking"
    UNKNOWN = "unknown"


class BROTDome(BROTBase):
    @property
    def shutter(self) -> DomeShutterStatus:
        match self._telemetry.AUXILIARY.DOME.REALPOS:
            case 0.0:
                return DomeShutterStatus.CLOSED
            case 0.5:
                return DomeShutterStatus.MOVING
            case 1.0:
                return DomeShutterStatus.OPEN
            case _:
                return DomeShutterStatus.UNKNOWN

    @property
    def in_motion(self) -> bool:
        return (self._telemetry.AUXILIARY.DOME.REALPOS == 0.5) or (
            self._telemetry.AUXILIARY.DOME.MOTION_STATE == 1.0
        )

    @property
    def azimuth(self) -> float:
        return self._telemetry.AUXILIARY.DOME.AZ

    @property
    def status(self) -> DomeStatus:
        match self._telemetry.AUXILIARY.DOME.READY_STATE:
            case 0.0:
                return DomeStatus.PARKED
            case -1.0:
                return DomeStatus.ERROR
            case 8.0:
                return DomeStatus.TRACKING
            case _:
                return DomeStatus.UNKNOWN

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

    async def start_tracking(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_track=1"
        )

    async def stop_tracking(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_track=0"
        )

    async def park(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_park=1"
        )

    async def reset(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command dome_reset=1"
        )


__all__ = ["BROTDome", "DomeStatus", "DomeShutterStatus"]
