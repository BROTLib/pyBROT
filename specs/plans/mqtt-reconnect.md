# Plan: MQTT auto-reconnect for `MQTTTransport`

Status: proposed (2026-09-14)

Issue: [pyobs/pyobs-brot#68](https://github.com/pyobs/pyobs-brot/issues/68) — "MQTT client does
not auto-reconnect after disconnect".

## Problem

`MQTTTransport.run()` (`src/pybrotlib/transport/mqtttransport.py:29-41`) opens the `aiomqtt.Client`
once inside a single `async with`, with no retry. `brotroof.py`'s `open()` (pyobs-brot) launches it
via a bare `asyncio.create_task(self.mqtt.run())` with nothing awaiting or wrapping it.

Two bugs, not one:

1. **No reconnect at all.** When the broker connection drops, `aiomqtt` raises `MqttError` out of
   the `async with` block, which propagates out of `run()` and kills the task silently (default
   asyncio unhandled-task-exception logging, nothing retries).
2. **`_connected` / `_connected_event` never reset.** `self._connected = True` and
   `self._connected_event.set()` are set once at connect time and never cleared on disconnect. So
   even after (1) is fixed with a reconnect loop, `publish()`'s `await self._connected_event.wait()`
   returns immediately on the stale event and calls `self._client.publish(...)` on a dead client —
   same `MqttCodeError: not currently connected` from the issue. Also means `Transport.connected`
   lies to callers (e.g. `BrotRoof._update_status_task` keeps "updating status" from stale telemetry
   after a disconnect, no error surfaced).

## Design

- Wrap the `async with Client(...)` in a `while not self._closing.is_set()` loop.
- On disconnect/`MqttError`: clear `_connected_event`, set `_connected = False`, log a warning,
  back off, retry.
- Exponential backoff: 1s, 2s, 4s, ... capped at 30s; reset to 1s after a successful (re)connect.
- Backoff sleep must be interruptible by `close()` — don't block a full 30s after `_closing` is set.
- No change to `publish()`'s public behavior: it already blocks on `_connected_event`, which is the
  correct behavior once the event is cleared on disconnect — callers just wait through an outage
  instead of racing ahead onto a stale client.

## Checklist

- [ ] Wrap `run()`'s connection block in a `while not self._closing.is_set(): try: ... except
      aiomqtt.MqttError: ...` reconnect loop.
- [ ] On disconnect/exception: `self._connected = False`, `self._connected_event.clear()`, log at
      warning level with the exception.
- [ ] Exponential backoff (1s → 2s → 4s → ... → cap 30s), reset on successful connect.
- [ ] Make the backoff wait interruptible by `_closing` (e.g. race `asyncio.wait_for(self._closing.wait(),
      timeout=backoff)` instead of a plain `asyncio.sleep`).
- [ ] Verify `close()` still exits the loop promptly (currently only checked inside the
      `async for message in client.messages` loop — needs the same check around the reconnect loop
      itself, otherwise `close()` during a backoff wait doesn't take effect until the wait ends).
- [ ] Unit test: `Client.__aenter__` raises `MqttError` once then succeeds — `run()` retries and
      `_connected_event` is only set after the second attempt.
- [ ] Unit test: simulate a disconnect after a successful connect — `_connected` goes back to
      `False`, and a `publish()` call issued during the outage blocks (doesn't raise) until
      reconnected.
- [ ] Bump `pybrotlib` version; update `pyobs-brot`'s dependency floor
      (`pyproject.toml`'s `pybrotlib>=1.1.5`) to match — same pattern as the earlier `pybrotlib`
      1.1.5 event-loop-starvation fix (see `pyobs-core/specs/plans/2026-07-22-ejabberd-throughput-benchmarking.md`,
      "A real, separate bug *was* found and fixed along the way").
- [ ] Close pyobs-brot#68, referencing the release.

## Non-goals

- Not changing `publish()`'s API or call sites.
- Not addressing broader event-loop-starvation issues (already fixed separately, see the linked
  plan above).
