from enum import Enum

from ..components.base import BROTBase


class MirrorCoverStatus(Enum):
    CLOSED = "closed"
    MOVING = "moving"
    OPEN = "open"
    UNKNOWN = "unknown"


class BROTMirrorCovers(BROTBase):
    @property
    def status(self) -> MirrorCoverStatus:
        match self._telemetry.AUXILIARY.COVER.REALPOS:
            case 0.0:
                return MirrorCoverStatus.CLOSED
            case 0.5:
                return MirrorCoverStatus.MOVING
            case 1.0:
                return MirrorCoverStatus.OPEN
            case _:
                return MirrorCoverStatus.UNKNOWN
