# Plan: multi-source weather publishing

Status: implemented, closed (2026-09-22). Shipped in `pybrotlib`
[1.3.0](https://github.com/BROTLib/pyBROT/releases/tag/v1.3.0); wired up downstream in
[BROTLib/BROTgui#5](https://github.com/BROTLib/BROTgui/pull/5) and
[pyobs/pyobs-brot#74](https://github.com/pyobs/pyobs-brot/pull/74).

Issue: [BROTLib/pyBROT#32](https://github.com/BROTLib/pyBROT/issues/32) — "Publish weather
station readings to BROTLib's {site}/Telescope/SET topic" (open).

## Problem

BROTLib now accepts live weather as inbound SET commands (landed at BROTLib@a07e388, closing
BROTLib/BROTLib#33): `FB_Comm_MQTT_Influx._handleMQTTMessage` understands
`command temperature=<degC>`, `command humidity=<%>`, `command pressure=<hPa>` on
`{site}/Telescope/SET`, buffered the same way as `rightascension`/`declination` already are
(`Temperature`/`Humidity`/`Pressure` fields on the FB instance). Nothing on the pyBROT side
publishes them yet.

We want to support more than one way to *get* the weather data (not every site sources it the
same way): [pyobs-weather](https://github.com/pyobs/pyobs-weather) — Tim's own weather-aggregator
service, exposing a public `GET /api/current/` — should be one source, with a simple local
JSON/YAML file as a second, source-agnostic option (hand-rolled sensor script, cron dump, manual
override).

**Staleness constraint** (checked directly against BROTLib@a07e388's diff): the PLC side has no
concept of staleness or quality. `Temperature`/`Humidity`/`Pressure` are plain `LREAL`s,
overwritten unconditionally on receipt — no timestamp or quality flag travels with the MQTT
message, and there's no protocol-level way to signal "this value is stale." Once a reading is
published, TwinCAT treats it as current forever, until the next publish. So pyBROT is the only
place that can decide a reading isn't trustworthy enough to send — this has to be enforced
entirely on the publish side, both per-field (one bad sensor at the station doesn't need to block
the other two) and by reading age (catches a source that's alive but returning a frozen/cached old
value).

## Design

New subpackage `src/pybrotlib/weather/`:

- **`source.py`**
  - `WeatherReading` (dataclass): `temperature: float | None`, `humidity: float | None`,
    `pressure: float | None`, `time: datetime | None`. A `None` field means "don't have it / don't
    trust it" and is never published.
  - `WeatherSource` (plain base class, matching `Transport`'s style in
    `src/pybrotlib/transport/transport.py` rather than `typing.Protocol`):
    `async def read(self) -> WeatherReading | None`, `None` = read failed entirely (network/file
    error), logged by the source itself.

- **`pyobs.py`**: `PyobsWeatherSource(base_url: str, client: httpx.AsyncClient | None = None)`
  - GETs `{base_url}/api/current/` (verified against
    `pyobs_weather/api/views.py::current` and `pyobs_weather/settings.py:145` — default sensor
    codes `temp`/`humid`/`press`, response shape
    `{"time": ..., "good": bool, "sensors": {"<code>": {"good": bool|None, "value": float|None}}}`,
    with `good` reported *per sensor code*, not just overall).
  - Maps `temp`→`temperature`, `humid`→`humidity`, `press`→`pressure`. A field is only populated
    if the response has that sensor code and its `good` is not `False`; otherwise left `None`.
  - `WeatherReading.time` comes from the response's top-level `time`.
  - Any HTTP/network error → log a warning, return `None` (nothing published that cycle, not an
    exception out of the publisher loop).

- **`file.py`**: `FileWeatherSource(path: str | Path)`
  - Re-reads the file on every call, so an external writer (cron job, manual edit) can update it
    between polls.
  - `.json` → `json.load`; `.yml`/`.yaml` → `yaml.safe_load`. Flat dict with optional
    `temperature`/`humidity`/`pressure`/`time` keys; missing keys → `None`.
  - Missing file / unparsable content → log a warning, return `None`.

- **`publisher.py`**: `WeatherPublisher(transport: Transport, site: str, source: WeatherSource,
  interval: float = 60.0, max_age: float | None = 300.0)`
  - `async def run(self) -> None`: loop until closed (own `asyncio.Event`, same shape as
    `Transport._closing`) — sleep `interval`, `reading = await source.read()`:
    - `None` → log at debug, skip this cycle.
    - `reading.time` set, `max_age` set, and the reading is older than `max_age` → log a warning,
      skip (this is the reading-level half of the staleness handling).
    - Otherwise, for each of `temperature`/`humidity`/`pressure` that is not `None`:
      `await transport.publish(f"{site}/Telescope/SET", f"command {name}={value}")` — same call
      shape already used by `BROTTelescope` (`src/pybrotlib/components/telescope.py:86-95`, e.g.
      `track()`).
  - `async def close(self) -> None`: sets the closing event, mirrors `Transport.close()`.

- **`__init__.py`**: exports `WeatherReading`, `WeatherSource`, `PyobsWeatherSource`,
  `FileWeatherSource`, `WeatherPublisher`.

### Dependencies (`pyproject.toml`)

- Add `httpx` — async HTTP client, needed by `PyobsWeatherSource`. Project currently depends only
  on `aiomqtt`.
- Add `pyyaml` as a direct dependency — currently only pulled in transitively (via dev tooling,
  per `uv.lock`), needed directly now for `FileWeatherSource`.
- No new *test* dependency: `PyobsWeatherSource` tests use `httpx.MockTransport` (built into
  `httpx`).

### Tests (`tests/`)

- `test_weather_source_file.py` — JSON fixture, YAML fixture, missing file, malformed content.
- `test_weather_source_pyobs.py` — `httpx.MockTransport` with a canned `/api/current/` payload:
  full good reading; one sensor `good: false` → that field `None`, others populated; HTTP error →
  `None`.
- `test_weather_publisher.py` — fake in-memory `WeatherSource` and `Transport` (same style as
  `tests/test_mqtttransport_reconnect.py`'s fakes): good reading → 3 `publish()` calls with the
  expected topic/payload strings; `None` reading → no publish; stale reading (old `time`,
  `max_age` exceeded) → no publish; partial reading (one field `None`) → only 2 publishes.

### README

Short "Weather" section under Components, matching the existing usage-snippet style —
`asyncio.create_task(weather_publisher.run())` alongside `transport.run()`.

### Example downstream wiring (BROTgui)

Not part of this repo's checklist (BROTgui is a separate repo), but illustrates why "no
config-file-driven source selection" in pyBROT (see Non-goals) is the right cut: `BROTgui/main.py`
already parses `config.yml` by hand (`BROTgui/BROTgui/main.py:33-44` — `mqtt.host`/`mqtt.port`,
`telescope.location`/`name`/`pointing`) and constructs `MyTransport`/`BROT` from it directly. A
weather source is the same kind of app-level glue, added the same way, e.g.:

```yaml
weather:
    source: pyobs                        # or "file"
    url: 'https://weather.example.org'   # pyobs source
    # path: '/path/to/weather.json'      # file source instead
    interval: 60
    max_age: 300
```

`main.py` would read `config.get("weather")` (absent → no weather publishing, e.g. sites without a
source yet, matching the already-commented-out MONETN/50cm blocks), pick
`PyobsWeatherSource(url)` or `FileWeatherSource(path)` based on `source`, build
`WeatherPublisher(mqtt, config["telescope"]["name"], source, interval=..., max_age=...)`, and
`asyncio.create_task(weather_publisher.run())` next to the existing `mqtt.run()` task. This glue
stays in BROTgui, not pybrotlib — consistent with `MQTTTransport`/`BROT` already being constructed
the same way there rather than pyBROT reading `config.yml` itself.

## Checklist

- [x] Add `httpx` and `pyyaml` to `pyproject.toml` dependencies (plus `types-PyYAML` as a dev-only
      mypy stub).
- [x] `src/pybrotlib/weather/source.py`: `WeatherReading`, `WeatherSource`.
- [x] `src/pybrotlib/weather/pyobs.py`: `PyobsWeatherSource`.
- [x] `src/pybrotlib/weather/file.py`: `FileWeatherSource`.
- [x] `src/pybrotlib/weather/publisher.py`: `WeatherPublisher`.
- [x] `src/pybrotlib/weather/__init__.py`: exports.
- [x] Unit tests for all three, including the publisher's skip logic (bad field, stale reading,
      missing source data).
- [x] README: short usage section.
- [x] `specs/index.md`: add a bullet for this plan doc.
- [x] Close BROTLib/pyBROT#32 once shipped, referencing the release (same pattern as
      `mqtt-reconnect.md`'s checklist item for pyobs-brot#68).

## Non-goals

- Not implementing every conceivable weather source now — just the abstraction plus pyobs-weather
  and a JSON/YAML file, as the two concrete ones. More can be added later behind the same
  `WeatherSource` base without touching `WeatherPublisher`.
- Not wiring anything on the BROTLib/TwinCAT side — already landed at BROTLib@a07e388, and nothing
  consumes the values there yet (per that commit's own message); that remains a separate,
  unscoped piece.
- Not adding config-file-driven source selection (e.g. a YAML app config that picks which
  `WeatherSource` to instantiate for you) — the caller wires up the source directly in Python,
  same as it already does for `MQTTTransport`/`BROT`.
