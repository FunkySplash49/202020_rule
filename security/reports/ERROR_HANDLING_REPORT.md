# Error Handling Security Report

## Status: HIGH (fixed, verified)

## Findings

The app has no API responses to leak through. The checklist's error-handling
risk shows up here in a different form: an exception in the wrong place could
leave the user unable to use their Mac.

1. **An overlay could get stuck on screen.** Before the fix, `overlay.py` had no
   exception handling. The countdown runs in an NSTimer block:

   ```python
   def _timer_fired(self, timer):
       self._tick()
   ```

   If `_tick()`, `_render()` or the fade-out completion raised, the timer
   stopped but the panels stayed up. Each panel sits at
   `NSScreenSaverWindowLevel` on every Space and swallows every click. The
   only other exit, "End now", runs through the same controller.

2. **Unhandled exceptions in callbacks crash the app.** The app tick
   (`twenty.py`), the sleep/wake observer, the icon setup and the "End now"
   target all ran bare. An exception escaping into AppKit can end the process,
   and with it the reminders.

3. **Development overrides were live in the shipped app.** `TWENTY_INTERVAL` and
   `TWENTY_IDLE_RESET` were read in the packaged `.app` too. This is the
   desktop equivalent of leaving debug mode on in production. See
   INPUT_VALIDATION_REPORT.md for why that matters.

4. **No logging.** Failures left no record.

## What's at risk

For finding 1: a panel at screen-saver level sits above normal windows and
most system UI, probably including the Force Quit dialog (Cmd+Opt+Esc; not
tested). The mouse can't reach anything underneath. The keyboard still
works, because the panels never take focus, but most users would not think to
kill the app from a terminal. In practice the Mac looks frozen.

For findings 2 and 4: the app quits without a trace and the user stops getting
breaks without knowing why.

## What's already secure

- The panels never become key windows, so the keyboard kept working even in
  the stuck state.
- Nothing is sent over the network, so errors can't leak data anywhere.
- `rumps` debug mode is off by default and the app never turns it on.

## Recommendations

1. Catch exceptions in every callback AppKit invokes, log them, and close the
   overlay instead of leaving it up.
2. Add a watchdog that runs on a separate timer and removes any overlay that
   outlives its schedule.
3. Make teardown close every panel even if one fails, and always reset state.
4. Ignore the development overrides in the packaged app.
5. Log failures to stderr, which the packaged app sends to the unified log.

## Verification results

All goals in plans/ERROR_HANDLING_PLAN.md pass. See the plan for the tests run.
