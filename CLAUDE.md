# TwentyTwenty — 20-20-20 eye-break menu bar app (macOS)

Every 20 minutes, show a fullscreen overlay on all displays: count down 5→1,
then run a 20-second break ("Look at something 20 feet away"), then fade out.

## Stack
- Python 3.13, `rumps` 0.4.0 (menu bar), PyObjC 12.2 (AppKit + Quartz) for the overlay
- `py2app` 0.28.10 for packaging into a standalone `.app`
- Local venv: `.venv/` (`python3 -m venv .venv && .venv/bin/pip install rumps pyobjc-framework-Cocoa pyobjc-framework-Quartz py2app`)

## Files
- `twenty.py`: entry point. `TwentyTwentyApp(rumps.App)` owns the 20-min cycle, the menu, and sleep/lock/idle handling.
- `overlay.py`: `OverlayController` (plain Python class) builds one panel per screen, handles the fades, runs the countdown/break state machine, and has the "End now" button.
- `setup.py`: py2app config. Build with `.venv/bin/python setup.py py2app`.
- `README.md`: user-facing docs, including the Login Items steps for auto-launch.
- `requirements.txt`: exact pins for every package (acts as the lock file). Install with `pip install -r requirements.txt`.
- `security/`: audit against the user's AGENTS.md / AI-CHECKLIST.md. Start at `security/AUDIT_SUMMARY.md`.
- `.gitignore`: ignores `.env*`, `.venv/`, `build/`, `dist/`.
- `CLAUDE.md`: this file.

Run in development: `.venv/bin/python twenty.py`
Fast test cycle: `TWENTY_INTERVAL=30 TWENTY_IDLE_RESET=600 .venv/bin/python twenty.py`
(Dev only. Ranges 5..86400 and 30..86400; bad values are logged and ignored. The packaged app, `sys.frozen`, ignores both.)

## Requirements (from the user)
- Overlay covers **every** display (`NSScreen.screens()`), borderless, dark semi-transparent background.
- Sits above all windows and all Spaces, including native-fullscreen apps.
- Fades in over about 0.4–0.6s (NSAnimationContext on window alpha). Fades out the same way.
- Countdown 5,4,3,2,1 (1s each), then a 20→0 break timer with an instruction line, then auto fade-out.
- "End now": small, borderless, low-contrast text button in a corner. It dismisses immediately (with fade) and resets the 20-min timer.
- Menu: status row ("Next break in Xm"), "Skip next reminder" toggle, "Quit".
- "Skip next reminder" is one-shot and session-only (not persisted). It suppresses the next break entirely, then turns itself off.

## Decisions confirmed by the user
1. **Clicks are blocked** everywhere on the overlay except "End now" (`setIgnoresMouseEvents_(False)` plus a 0.88-alpha background).
2. **Keyboard input is NEVER blocked.** The overlay must not take focus: panels use
   `NSWindowStyleMaskNonactivatingPanel`, and `canBecomeKeyWindow` / `canBecomeMainWindow` return `False`.
   Typing keeps going to the user's frontmost app. There is no Esc shortcut. Don't add `makeKeyWindow`,
   `activateIgnoringOtherApps`, or event taps to the overlay.
3. **Sleep / screen lock resets the cycle.** Suspend on `NSWorkspaceWillSleepNotification` and
   `com.apple.screenIsLocked`, and dismiss any visible overlay without animation. On `NSWorkspaceDidWakeNotification` /
   `com.apple.screenIsUnlocked`, start a fresh 20 minutes. Idle ≥ 5 min (`CGEventSourceSecondsSinceLastEventType`)
   holds the cycle at 20 min, so it restarts when the user returns. Trade-off: watching a long video without
   touching the input devices postpones breaks.
4. **After a skipped break**, the next one comes 20 min after the skipped time (so breaks end up 40 min apart). No "Take break now" item.
5. Both a natural finish and "End now" restart the 20-min cycle.

## Implementation notes / gotchas
- Window level `NSScreenSaverWindowLevel`. Collection behavior: `CanJoinAllSpaces | FullScreenAuxiliary | Stationary | IgnoresCycle`.
- `setHidesOnDeactivate_(False)` is required, because NSPanel hides when the app is inactive, and this app is always inactive.
- `setReleasedWhenClosed_(False)` on panels to avoid a PyObjC double release.
- The "End now" button subclass returns `acceptsFirstMouse_ → True`, so one click works on a non-key panel.
- **Don't use `rumps.Timer`.** It only runs in `NSDefaultRunLoopMode` and stalls while the menu is open.
  Use `NSTimer.timerWithTimeInterval_repeats_block_` added to `NSRunLoopCommonModes`.
- The status icon is the SF Symbol `eye` as a template image, installed in `rumps.events.before_start`
  (after rumps creates `_nsapp.nsstatusitem`). The emoji title `👁` is the fallback.
- Menu items without a callback are greyed out by rumps. The status row uses this on purpose.
- `time.monotonic()` is used for deadlines. Sleep handling resets the cycle, so pausing during sleep doesn't matter.

## Security rules (from the audit, keep these)
- Every callback AppKit invokes (NSTimer blocks, button targets, notification observers, animation
  completions) must catch exceptions and log them. An exception escaping into AppKit can kill the app.
- A failure during a break must close the overlay, never leave it up: `OverlayController.force_close()`.
  The app tick calls `overlay.close_if_stuck()` every second as a watchdog; don't remove it.
- Validate any new input (env vars, settings) with explicit ranges; keep dev knobs off when `sys.frozen`.
- Pin new dependencies with `==` in `requirements.txt` and run `pip-audit -r requirements.txt` from a separate venv.

## Status
Working end to end. `overlay.py`, `twenty.py`, `setup.py`, `README.md` are complete and
`dist/TwentyTwenty.app` builds and launches.

Verified by scripted tests (no manual clicking):
- Panels appear on every `NSScreen`, window level 1000, alpha animates 0 -> 1, never key windows.
- Countdown advances; "End now" (through the real button target/action) dismisses and reports `ended_early=True`;
  a completed break reports `False`. 4/4 runs correct after the fix below.
- Full app cycle with `TWENTY_INTERVAL=6`: status line counts down, "Skip next reminder" suppressed exactly one
  break and switched itself off, the cycle restarted after the skip, and the next break ran and reset the cycle.
- `dist/TwentyTwenty.app/Contents/MacOS/TwentyTwenty` launches with no errors and runs as a background (menu bar) process.

### FIXED: intermittent wrong `ended_early`
Cause: `OverlayController` subclassed `NSObject`, so its methods became Objective-C selectors and the keyword
argument in `dismiss(ended_early=False)` did not reliably survive the round trip, leaving the default `True`.
This also explains why an earlier debug run that monkey-patched `dismiss` with a plain Python function always
reported the flag correctly.
Fix: `OverlayController` is now a plain Python class. Only `_ButtonTarget(NSObject)` remains an Objective-C
object, because an NSButton target has to be one.
**Rule: don't turn OverlayController back into an NSObject subclass**, and avoid keyword arguments on methods
of any NSObject subclass here.

### Still unverified (needs a human, can't be scripted here)
- Overlay over an app in native fullscreen, and on a second physical display.
- Clicking "End now" with a real mouse (only `performClick_` was tested).
- Typing into another app while the overlay is up.
- The menu status line updating while the menu is held open.
- `screencapture` fails in this environment (no Screen Recording permission), so there are no visual screenshots
  of the overlay; appearance (font sizes, button placement, contrast) has never been seen, only computed.

### Possible next steps
- Code-sign the bundle so it opens on other Macs without the right-click-Open dance.
- Handle displays being connected/disconnected while an overlay is on screen (panels are built at show time only).
