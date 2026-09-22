# Design/planning docs

- `plans/2026-09-22-weather-sources.md` — pluggable `WeatherSource` (pyobs-weather + local
  JSON/YAML) and a `WeatherPublisher` that publishes temperature/humidity/pressure onto
  `{site}/Telescope/SET`, closing pyBROT#32.
- `plans/2026-09-14-mqtt-reconnect.md` — fix `MQTTTransport` to auto-reconnect on disconnect and
  stop lying about connection state, closing pyobs-brot#68.
- `pyobs-core/specs/plans/2026-09-14-brot-settle-loop-staleness-and-resend.md` (`pyobs/pyobs-core`,
  not this repo) — adds `Transport.telemetry_age()` here, used by a `pyobs-brot`-side settle-loop
  helper to detect stalled telemetry and resend idempotent setpoints; addresses pyobs-brot#61.
