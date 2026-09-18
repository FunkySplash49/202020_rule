# Error Handling Fix Plan

## Changes

- `overlay.py`: wrap `_timer_fired`, `show()` and `_ButtonTarget.endNow_` in
  try/except. On failure, log and call `force_close()`.
- `overlay.py`: add `close_if_stuck()`. `show()` records a deadline (lead-in +
  break + both fades + `STUCK_GRACE_SECONDS`). Past it, the overlay is torn
  down without animation.
- `overlay.py`: add `force_close()`, which stops the timer and tears down
  immediately without raising.
- `overlay.py`: `_teardown()` closes each panel in its own try/except, always
  clears `_panels` and `_phase`, and guards the `on_finish` callback.
- `twenty.py`: the app timer calls `_timer_fired`, which wraps `_tick()` and
  checks `overlay.close_if_stuck()` every second.
- `twenty.py`: guard the sleep/wake observer callbacks and `_install_icon`.
- `twenty.py`: skip the environment overrides when `sys.frozen` is set (the
  py2app bundle).
- `twenty.py`: configure `logging` in `__main__`.

## New files

None.

## Verification goals

- [x] If the overlay's timer dies mid-break, the app's watchdog removes every
      panel once the deadline passes (test: stop the timer after `show()`).
- [x] Before the deadline, the watchdog leaves a healthy overlay alone.
- [x] An exception inside the countdown tick closes the overlay and is logged.
      The process keeps running (test: make `_render` raise).
- [x] "End now" followed by a completed break still reports
      `ended_early = [True, False]` (regression check).
- [x] The packaged app launched with `TWENTY_INTERVAL=0` keeps running, logs
      nothing and schedules no early break.

Test script: `failsafe_test.py` from the audit session (all four checks
printed PASS). Not kept in the repo; the checks above describe it.

## Manual verification (for the human)

- Run the app for a full day and check Console.app (filter "TwentyTwenty")
  for ERROR lines.
- Press Cmd+Opt+Esc while an overlay is up and note whether the Force Quit
  window shows above it. If it doesn't, the watchdog is the only automatic way
  out of a stuck overlay, which is one more reason to keep it.
