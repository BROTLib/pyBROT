from .components import *
from .transport import Transport


class BROT:
    def __init__(self, transport: Transport, telescope_name: str):
        self.dome = BROTDome(transport, telescope_name)
        self.roof = BROTRoof(transport, telescope_name)
        self.focus = BROTFocus(transport, telescope_name)
        self.mirrorcovers = BROTMirrorCovers(transport, telescope_name)
        self.telescope = BROTTelescope(transport, telescope_name)


__all__ = ["BROT"]
