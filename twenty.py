"""TwentyTwenty: a menu bar app that enforces the 20-20-20 rule.

Every 20 minutes a fullscreen overlay covers all displays, counts down 5..1,
then runs a 20-second break asking you to look 20 feet away.

Timer rules
-----------
* The 20-minute cycle restarts whenever a break ends (naturally or via
  "End now") and whenever a break is suppressed by "Skip next reminder".
* Sleep or screen lock pauses the cycle; on wake/unlock a fresh 20 minutes
  starts (you were already away from the screen).
* Being idle (no keyboard/mouse input) for IDLE_RESET_SECONDS counts the same
  way: the cycle restarts once you return. Note this also means a long video
  watched without touching the input devices will postpone breaks.

Environment overrides, for development only:
  TWENTY_INTERVAL=30 python twenty.py      # break every 30 seconds
  TWENTY_IDLE_RESET=600 python twenty.py   # idle threshold in seconds
Values must be whole numbers inside the ranges in _env_seconds(); anything
else is logged and ignored. The packaged .app ignores both variables, so
nothing outside the app can change its schedule.
"""

import logging
import math
import os
import sys
import time

import objc
import rumps
from AppKit import NSImage, NSWorkspace
from Foundation import (
    NSDistributedNotificationCenter,
    NSObject,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSTimer,
)
from Quartz import (
    CGEventSourceSecondsSinceLastEventType,
    kCGAnyInputEventType,
    kCGEventSourceStateCombinedSessionState,
)

from overlay import OverlayController

APP_NAME = "TwentyTwenty"
FALLBACK_TITLE = "👁"

log = logging.getLogger(APP_NAME)

# py2app sets sys.frozen inside the built .app.
IS_PACKAGED = bool(getattr(sys, "frozen", False))


def _env_seconds(name, default, minimum, maximum):
    """Read a development override, falling back to `default` on bad input.

    A 0 or negative interval would bring the overlay straight back after
    every "End now", keeping the screen covered and clicks blocked, so values
    below `minimum` are rejected rather than clamped.
    """
    if IS_PACKAGED:
        return default
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        log.warning("Ignoring %s=%r: not a whole number", name, raw)
        return default
    if not minimum <= value <= maximum:
        log.warning("Ignoring %s=%d: must be between %d and %d", name, value, minimum, maximum)
        return default
    return value


BREAK_INTERVAL_SECONDS = _env_seconds("TWENTY_INTERVAL", 20 * 60, minimum=5, maximum=24 * 3600)
IDLE_RESET_SECONDS = _env_seconds("TWENTY_IDLE_RESET", 5 * 60, minimum=30, maximum=24 * 3600)


def _seconds_idle():
    return CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType
    )


class _SystemObserver(NSObject):
    """Bridges sleep/wake and lock/unlock notifications to Python callbacks."""

    def initWithSuspend_resume_(self, on_suspend, on_resume):
        self = objc.super(_SystemObserver, self).init()
        if self is None:
            return None
        self._on_suspend = on_suspend
        self._on_resume = on_resume

        ws = NSWorkspace.sharedWorkspace().notificationCenter()
        ws.addObserver_selector_name_object_(self, "suspend:", "NSWorkspaceWillSleepNotification", None)
        ws.addObserver_selector_name_object_(self, "resume:", "NSWorkspaceDidWakeNotification", None)

        dist = NSDistributedNotificationCenter.defaultCenter()
        dist.addObserver_selector_name_object_(self, "suspend:", "com.apple.screenIsLocked", None)
        dist.addObserver_selector_name_object_(self, "resume:", "com.apple.screenIsUnlocked", None)
        return self

    def suspend_(self, note):
        try:
            self._on_suspend(note.name())
        except Exception:
            log.exception("Suspend handler failed")

    def resume_(self, note):
        try:
            self._on_resume(note.name())
        except Exception:
            log.exception("Resume handler failed")


class TwentyTwentyApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title=FALLBACK_TITLE, quit_button="Quit")

        self.status_item = rumps.MenuItem("Next break in 20m")  # no callback -> greyed-out info row
        self.skip_item = rumps.MenuItem("Skip next reminder", callback=self.toggle_skip)
        self.menu = [self.status_item, None, self.skip_item, None]

        self.skip_next = False
        self.suspended = False       # asleep / screen locked
        self.was_idle = False
        self.next_break_at = 0.0
        self._reset_cycle()

        self.overlay = OverlayController(self._on_break_finished)
        self.observer = _SystemObserver.alloc().initWithSuspend_resume_(self._suspend, self._resume)

        # rumps.Timer only runs in the default run-loop mode, which stalls while the
        # status menu is open; use a common-modes NSTimer so the menu stays live.
        self._tick_timer = NSTimer.timerWithTimeInterval_repeats_block_(1.0, True, self._timer_fired)
        NSRunLoop.mainRunLoop().addTimer_forMode_(self._tick_timer, NSRunLoopCommonModes)

        rumps.events.before_start.register(self._install_icon)

    # ----------------------------------------------------------------- setup

    def _install_icon(self):
        """Use the SF Symbol eye as a template image; keep the emoji title as fallback."""
        try:
            img = NSImage.imageWithSystemSymbolName_accessibilityDescription_("eye", APP_NAME)
            if img is None:
                return
            img.setTemplate_(True)
            button = self._nsapp.nsstatusitem.button()
            button.setImage_(img)
            button.setTitle_("")
        except Exception:
            log.exception("Could not set menu bar icon; keeping the emoji title")

    # ----------------------------------------------------------------- cycle

    def _reset_cycle(self):
        self.next_break_at = time.monotonic() + BREAK_INTERVAL_SECONDS
        self._update_status()

    def _timer_fired(self, timer):
        # An exception escaping into AppKit would crash the app, so log it and
        # keep the timer running; the next tick gets another chance.
        try:
            self._tick()
        except Exception:
            log.exception("Tick failed")

    def _tick(self):
        if self.overlay.close_if_stuck():
            self._reset_cycle()
            return
        if self.suspended or self.overlay.is_showing():
            self._update_status()
            return

        if _seconds_idle() >= IDLE_RESET_SECONDS:
            # Away from the keyboard: eyes are resting. Hold the cycle at a full
            # 20 minutes so it starts fresh when the user returns.
            self.was_idle = True
            self._reset_cycle()
            return
        if self.was_idle:
            self.was_idle = False
            self._reset_cycle()

        if time.monotonic() >= self.next_break_at:
            if self.skip_next:
                self._set_skip(False)   # one-shot: consumed by this break
                self._reset_cycle()
            else:
                self.overlay.show()
        self._update_status()

    def _on_break_finished(self, ended_early):
        # Both "End now" and a completed break start a fresh 20-minute cycle.
        self._reset_cycle()

    def _suspend(self, reason):
        self.suspended = True
        if self.overlay.is_showing():
            self.overlay.dismiss(ended_early=True, animated=False)
        self._update_status()

    def _resume(self, reason):
        self.suspended = False
        self.was_idle = False
        self._reset_cycle()

    # ------------------------------------------------------------------ menu

    def toggle_skip(self, sender):
        self._set_skip(not self.skip_next)

    def _set_skip(self, value):
        self.skip_next = value
        self.skip_item.state = 1 if value else 0
        self._update_status()

    def _update_status(self):
        if self.overlay_showing():
            text = "Break in progress"
        elif self.suspended:
            text = "Paused (asleep or locked)"
        elif self.was_idle:
            text = "Paused while you're away"
        else:
            remaining = max(0, self.next_break_at - time.monotonic())
            if remaining >= 60:
                when = f"{math.ceil(remaining / 60)}m"
            else:
                # ceil for minutes (a fresh cycle should read "20m"), floor for
                # seconds (so the last minute ticks 59,58,... instead of jumping).
                when = f"{int(remaining)}s"
            text = f"Skipping break in {when}" if self.skip_next else f"Next break in {when}"
        self.status_item.title = text

    def overlay_showing(self):
        overlay = getattr(self, "overlay", None)
        return overlay is not None and overlay.is_showing()


if __name__ == "__main__":
    # stderr from the packaged app goes to the unified log (Console.app).
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    TwentyTwentyApp().run()
