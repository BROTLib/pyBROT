# pyBROTlib

Python interface to BROT telescopes, talking to the telescope's TwinCAT/PLC control system
over MQTT.

## Installation

```bash
uv add pybrotlib
```

## Usage

Connect a transport (currently MQTT) to a named telescope and drive it through the `BROT`
object:

```python
import asyncio

from pybrotlib import BROT
from pybrotlib.transport import MQTTTransport


async def main() -> None:
    transport = MQTTTransport(host="localhost", port=1883)
    brot = BROT(transport, "MyTelescope")

    # the transport needs its own task to receive telemetry/publish commands
    asyncio.create_task(transport.run())
    await asyncio.sleep(2)  # give it a moment to connect and receive first telemetry

    await brot.telescope.track(ra=10.5, dec=41.2)
    print(brot.telescope.status)


asyncio.run(main())
```

`transport.telemetry` holds the live telemetry tree (see `pybrotlib/telemetry.py`), which is
kept up to date by messages received on `<telescope>/.../Telemetry` topics and read by the
component properties below.

## Components

Each `BROT` instance exposes one component per subsystem, all constructed from the same
transport and telescope name:

- **`telescope`** (`BROTTelescope`) — pointing (`track`, `move`), offsets (`set_offset_ha`,
  `set_offset_dec`, `set_offset_alt`, `set_offset_az`), power/park/stop/reset, and status
  (`status`, `motion_state`, `global_status`).
- **`focus`** (`BROTFocus`) — `position`, `set(focus)`, `powered`, `referenced`.
- **`dome`** (`BROTDome`) — shutter/tracking state, `open`, `close`, `start_tracking`,
  `stop_tracking`, `park`, `reset`.
- **`roof`** (`BROTRoof`) — roll-off roof state, `open`, `close`, `stop`, `reset`.
- **`mirrorcovers`** (`BROTMirrorCovers`) — `status`, `open`, `close`.

All commands are fire-and-forget MQTT publishes; callers are expected to poll telemetry
(directly, or via the component's status properties) to observe the result.

## Weather

`pybrotlib.weather` publishes live temperature/humidity/pressure onto a telescope's
`{site}/Telescope/SET` topic, for sites where a Python process has access to a weather source.
Pick a `WeatherSource` and hand it to a `WeatherPublisher` alongside your transport:

```python
from pybrotlib.weather import PyobsWeatherSource, WeatherPublisher
# or: from pybrotlib.weather import FileWeatherSource

source = PyobsWeatherSource("https://weather.example.org")
weather = WeatherPublisher(transport, "MyTelescope", source, interval=60, max_age=300)

asyncio.create_task(weather.run())
```

`max_age` (seconds) guards against publishing a stale reading: BROTLib has no way to tell a fresh
value from a stale one once it's received, so a source that's alive but returning an old cached
reading is caught here instead. A reading missing one field (e.g. a broken pressure sensor) still
publishes the fields it does have.

## Development

```bash
uv sync --group dev
uv run pytest
```
