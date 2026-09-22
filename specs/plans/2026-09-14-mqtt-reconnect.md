# Plan: MQTT auto-reconnect for `MQTTTransport`

Status: implemented, closed (2026-09-14). Shipped in `pybrotlib`
[1.2.1](https://github.com/BROTLib/pyBROT/releases/tag/v1.2.1); `pyobs-brot`'s floor bumped to
match and released as [2.0.3](https://github.com/pyobs/pyobs-brot/releases/tag/v2.0.3).

Issue: [pyobs/pyobs-brot#68](https://github.com/pyobs/pyobs-brot/issues/68) — "MQTT client does
not auto-reconnect after disconnect" (closed).

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

- [x] Wrap `run()`'s connection block in a `while not self._closing.is_set(): try: ... except
      aiomqtt.MqttError: ...` reconnect loop.
- [x] On disconnect/exception: `self._connected = False`, `self._connected_event.clear()`, log at
      warning level with the exception.
- [x] Exponential backoff (1s → 2s → 4s → ... → cap 30s), reset on successful connect.
- [x] Make the backoff wait interruptible by `_closing` (raced via `asyncio.wait_for(self._closing.wait(),
      timeout=backoff)` instead of a plain `asyncio.sleep`).
- [x] Verify `close()` still exits the loop promptly.
- [x] Unit test: `Client.__aenter__` raises `MqttError` once then succeeds — `run()` retries and
      `_connected_event` is only set after the second attempt
      (`tests/test_mqtttransport_reconnect.py::test_run_retries_after_connect_failure`).
- [x] Unit test: simulate a disconnect after a successful connect — `_connected` goes back to
      `False`, and a `publish()` call issued during the outage blocks (doesn't raise) until
      reconnected (`tests/test_mqtttransport_reconnect.py::test_publish_blocks_across_disconnect_and_reconnect`).
- [x] Bump `pybrotlib` version (1.2.0 → 1.2.1); update `pyobs-brot`'s dependency floor to
      `pybrotlib>=1.2.1` and release `pyobs-brot` 2.0.3 to match — same pattern as the earlier
      `pybrotlib` 1.1.5 event-loop-starvation fix (see
      `pyobs-core/specs/plans/2026-07-22-ejabberd-throughput-benchmarking.md`, "A real, separate bug
      *was* found and fixed along the way").
- [x] Close pyobs-brot#68, referencing the release.

## Implementation note

The first pass put the `_connected`/`_connected_event` reset in a `finally` attached to the whole
`try/except`, which only runs *after* the `except` block's own backoff `await` completes — so
`publish()` didn't actually block during the backoff window, reproducing bug #2 inside the fix
meant to close it. Caught by
`test_publish_blocks_across_disconnect_and_reconnect` failing on the first run. Fixed by resetting
state immediately at the top of the `except` block, before the backoff wait.

## Non-goals

- Not changing `publish()`'s API or call sites.
- Not addressing broader event-loop-starvation issues (already fixed separately, see the linked
  plan above).
