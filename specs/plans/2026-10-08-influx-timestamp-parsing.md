# Plan: accept the optional Influx timestamp on telemetry lines

Status: in progress (2026-10-08)

Issue: [BROTLib/pyBROT#40](https://github.com/BROTLib/pyBROT/issues/40). Prerequisite for
BROTLib/BROTLib#38 (retained boolean telemetry gets a trailing unix-ns timestamp).

## Problem

`MQTTTransport._process_message` (`src/pybrotlib/transport/mqtttransport.py`) takes everything
after the first `=` as the value. A line like `0 HYDRAULICS.BRAKEOPEN=true 1791449700123456700`
gives the value `true 1791449700123456700`: bools read as `False` (silently), int/float raise (logged
and dropped), strings keep the timestamp. `self.data[key]` gets the polluted value too.

## Approach

- New module-level helper `_split_field(field) -> tuple[str, str] | None` that returns `(key, value)`:
  - key is everything before the first `=`; empty key or no `=` returns `None` (malformed).
  - if the value starts with `"`, it runs to the closing unescaped `"` (backslash escapes the next
    char) and keeps the surrounding quotes, as before. No closing quote: take the rest.
  - otherwise the value ends at the next space.
  - anything after that (the timestamp) is dropped.
- `_process_message` uses the helper before `self.data[key] = ...`, so `data` and the typed
  telemetry see the same clean value. Type conversion stays unchanged.
- Out of scope: multi-field lines (`a=1,b=2`, BROTLib#39 / pyBROT#37).

## Checklist

- [ ] Add `_split_field` and use it in `_process_message`.
- [ ] Tests in `tests/test_mqtttransport.py`: bool/int/float/string each with and without trailing
      timestamp; quoted string with spaces (and `=`) with and without timestamp; `data` has no
      timestamp; escaped quote inside a string.
- [ ] `ruff`, `black`, `pyrefly`, `pytest`.
- [ ] Release pyBROT, then bump the floor in BROTgui and pyobs-brot, before any BROTLib release with
      #38 is deployed (not part of this change).
