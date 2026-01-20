from ..components.base import BROTBase


class BROTFocus(BROTBase):
    @property
    def position(self) -> float:
        return self._telemetry.POSITION.INSTRUMENTAL.FOCUS.CURRPOS

    async def set(self, focus: float) -> None:
        await self._transport.publish(
            f"{self._telescope_name}/Telescope/SET", f"command focus={focus}"
        )

    @property
    def powered(self) -> bool:
        return self._telemetry.POSITION.INSTRUMENTAL.FOCUS.POWER_STATE == 1.0

    @property
    def referenced(self) -> bool:
        return self._telemetry.POSITION.INSTRUMENTAL.FOCUS.REFERENCED == 1.0


__all__ = ["BROTFocus"]
