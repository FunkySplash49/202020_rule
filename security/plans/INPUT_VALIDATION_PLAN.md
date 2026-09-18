# Input Validation Fix Plan

## Changes

- `twenty.py`: add `_env_seconds(name, default, minimum, maximum)`. It returns
  the default when running as the packaged app, when the variable is unset,
  when it isn't a whole number, or when it falls outside the range. Rejected
  values are logged.
- `twenty.py`: `TWENTY_INTERVAL` must be 5 to 86,400 seconds.
  `TWENTY_IDLE_RESET` must be 30 to 86,400 seconds.

Out-of-range values are rejected, not clamped. A typo like `0` for `60` should
fall back to the safe default, not quietly become the 5-second minimum.

## New files

None.

## Verification goals

- [x] `TWENTY_INTERVAL=abc` logs a warning and uses 1200.
- [x] `TWENTY_INTERVAL=0`, `-5`, `3` and `99999999` each log a warning and use 1200.
- [x] `TWENTY_INTERVAL=30` is accepted in development.
- [x] With `sys.frozen` set, `TWENTY_INTERVAL=30` is ignored (1200 / 300).
- [x] The rebuilt `.app` launched with `TWENTY_INTERVAL=0` runs normally.

## Manual verification (for the human)

None needed.
