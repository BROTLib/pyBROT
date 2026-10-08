import asyncio
import logging

from aiomqtt import MqttError
from astropy.time import Time
from astropy.utils import iers

from ..transport import Transport

log = logging.getLogger(__name__)


class Dut1Publisher:
    """Periodically pushes UT1-UTC (seconds) to the PLC, which uses it for its pointing correction.

    The value comes from the IERS-A table bundled with astropy-iers-data, never from a download. It
    drifts slowly, but is republished often because the PLC reverts to 0.0 when no fresh value
    arrives within its staleness window.
    """

    def __init__(self, transport: Transport, site: str, interval: float = 60.0) -> None:
        self.transport = transport
        self.site = site
        self.interval = interval
        self._table = iers.IERS_A.open(iers.IERS_A_FILE)
        self._closing = asyncio.Event()

    async def close(self) -> None:
        self._closing.set()

    async def run(self) -> None:
        while not self._closing.is_set():
            try:
                await self._publish_once()
            except (MqttError, TimeoutError) as e:
                # a failed publish must not end the publisher; retry on the next interval
                log.warning("Could not publish dut1 to %s (%s).", self.site, e)
            try:
                await asyncio.wait_for(self._closing.wait(), timeout=self.interval)
                return
            except TimeoutError:
                pass

    async def _publish_once(self) -> None:
        dut1 = self._read()
        if dut1 is None:
            return
        await self.transport.publish(f"{self.site}/Telescope/SET", f"command dut1={dut1}")

    def _read(self) -> float | None:
        try:
            with iers.earth_orientation_table.set(self._table):
                return float(Time.now().delta_ut1_utc)
        except Exception as e:
            # e.g. the bundled table no longer covers today; don't send a made-up value, the PLC falls back to 0.0
            log.warning("Could not determine UT1-UTC (%s), not publishing.", e)
            return None


__all__ = ["Dut1Publisher"]
