from enum import Enum
from typing import Any

from ..components.base import BROTBase


class TelescopeStatus(Enum):
    PARKED = "parked"
    ONLINE = "online"
    ERROR = "error"
    INITPARK = "initpark"


class GlobalTelescopeStatus(Enum):
    NOTELESCOPE = "notelescope"
    OPERATIONAL = "operational"
    PANIC = "panic"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    UNKNOWN = "unknown"


class BROTAxis(BROTBase):
    def __init__(self, name: str, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._axis_name = name

    @property
    def error_state(self) -> int:
        return int(
            getattr(self._telemetry.POSITION.INSTRUMENTAL, self._axis_name).ERROR_STATE
        )


class BROTTelescope(BROTBase):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.alt = BROTAxis("ALT", *args, **kwargs)
        self.az = BROTAxis("AZ", *args, **kwargs)
        self.ha = BROTAxis("HA", *args, **kwargs)
        self.dec = BROTAxis("DEC", *args, **kwargs)
        self.focus = BROTAxis("FOCUS", *args, **kwargs)

    @property
    def name(self) -> str:
        return self._telemetry.TELESCOPE.INFO.NAME

    @property
    def diameter(self) -> float:
        return self._telemetry.TELESCOPE.INFO.DIAMETER

    @property
    def cabinet(self) -> str:
        return self._telemetry.TELESCOPE.INFO.CABINET

    @property
    def manufacturer(self) -> str:
        return self._telemetry.TELESCOPE.INFO.MANUFACTURER

    @property
    def mount_options(self) -> str:
        return self._telemetry.TELESCOPE.CONFIG.MOUNTOPTIONS

    @property
    def mount(self) -> str:
        return self._telemetry.TELESCOPE.CONFIG.MOUNT

    async def track(self, ra: float, dec: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", f"command rightascension={ra}"
        )
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", f"command declination={dec}"
        )
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command track=1"
        )

    async def move(self, alt: float, az: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", f"command elevation={alt}"
        )
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", f"command azimuth={az}"
        )
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command slew=1"
        )

    @property
    def offset_ha(self) -> float:
        return self._telemetry.POSITION.INSTRUMENTAL.HA.OFFSET * 3600.0

    async def set_offset_ha(self, offset: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET",
            f"command hourangleoffset={offset/3600.}",
        )

    @property
    def offset_dec(self) -> float:
        return self._telemetry.POSITION.INSTRUMENTAL.DEC.OFFSET * 3600.0

    async def set_offset_dec(self, offset: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET",
            f"command declinationoffset={offset/3600.}",
        )

    @property
    def offset_alt(self) -> float:
        return self._telemetry.POSITION.INSTRUMENTAL.ALT.OFFSET * 3600.0

    async def set_offset_alt(self, offset: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET",
            f"command elevationoffset={offset/3600.}",
        )

    @property
    def offset_az(self) -> float:
        return self._telemetry.POSITION.INSTRUMENTAL.AZ.OFFSET * 3600.0

    async def set_offset_az(self, offset: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET",
            f"command azimuthoffset={offset/3600.}",
        )

    @property
    def status(self) -> TelescopeStatus:
        match self._telemetry.TELESCOPE.READY_STATE:
            case 0.0:
                return TelescopeStatus.PARKED
            case 1.0:
                return TelescopeStatus.ONLINE
            case -1.0:
                return TelescopeStatus.ERROR
            case _:
                return TelescopeStatus.INITPARK

    @property
    def global_status(self) -> GlobalTelescopeStatus:
        match self._telemetry.TELESCOPE.STATUS.GLOBAL:
            case -1.0:
                return GlobalTelescopeStatus.NOTELESCOPE
            case 0.0:
                return GlobalTelescopeStatus.OPERATIONAL
            case 1.0:
                return GlobalTelescopeStatus.PANIC
            case 2.0:
                return GlobalTelescopeStatus.ERROR
            case 4.0:
                return GlobalTelescopeStatus.WARNING
            case 8.0:
                return GlobalTelescopeStatus.INFO
            case _:
                return GlobalTelescopeStatus.UNKNOWN

    @property
    def initpark(self) -> float:
        return self._telemetry.TELESCOPE.READY_STATE * 100.0

    async def power_on(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command power=true"
        )

    async def stop(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command stop=TRUE"
        )

    async def park(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command park=true"
        )

    async def reset(self) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", "command reset=1"
        )


__all__ = ["BROTTelescope", "TelescopeStatus", "GlobalTelescopeStatus"]
