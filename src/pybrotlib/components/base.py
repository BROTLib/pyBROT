from ..transport import Transport


class BROTBase:
    def __init__(self, transport: Transport, telescope_name: str):
        self._transport = transport
        self._telemetry = self._transport.telemetry
        self._telescope_name = telescope_name


__all__ = ["BROTBase"]
