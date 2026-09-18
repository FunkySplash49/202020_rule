"""Fullscreen break overlay: one borderless panel per display, faded in/out
with NSAnimationContext, running a 5-second lead-in countdown followed by the
20-second break timer.

Design notes
------------
* Windows are NSPanels with NSWindowStyleMaskNonactivatingPanel, so showing
  the overlay (or clicking "End now") never activates this app or steals
  keyboard focus from whatever the user is typing into. Keyboard input is
  never intercepted -- see CLAUDE.md, this is deliberate.
* The panels do NOT ignore mouse events and have a semi-opaque background, so
  clicks anywhere on the overlay are swallowed. Only the "End now" button
  reacts (it accepts first-mouse so a single click works on a non-key panel).
* Timers are added to NSRunLoopCommonModes so the countdown keeps ticking
  while a menu (e.g. our status menu) is being tracked.
* OverlayController is a plain Python class on purpose. When it subclassed
  NSObject, its methods became Objective-C selectors and keyword arguments
  such as dismiss(ended_early=False) did not survive the round trip, so a
  completed break was intermittently reported as ended early. Only the button
  target below needs to be an Objective-C object.
"""

import logging
import time

import objc
from AppKit import (
    NSAnimationContext,
    NSBackingStoreBuffered,
    NSButton,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSFontWeightLight,
    NSFontWeightRegular,
    NSForegroundColorAttributeName,
    NSMakeRect,
    NSPanel,
    NSScreen,
    NSScreenSaverWindowLevel,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import (
    NSAttributedString,
    NSObject,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSTimer,
)

LEAD_IN_SECONDS = 5
BREAK_SECONDS = 20
FADE_IN_SECONDS = 0.5
FADE_OUT_SECONDS = 0.5

BACKGROUND_ALPHA = 0.88
INSTRUCTION_TEXT = "Look at something 20 feet away"
LEAD_IN_TEXT = "Eye break starting…"

# An overlay still on screen this many seconds past its scheduled end is
# treated as stuck and torn down (see OverlayController.close_if_stuck).
STUCK_GRACE_SECONDS = 10

log = logging.getLogger(__name__)


def _schedule_repeating(interval, block):
    """Repeating NSTimer that also fires during menu tracking."""
    timer = NSTimer.timerWithTimeInterval_repeats_block_(interval, True, block)
    NSRunLoop.mainRunLoop().addTimer_forMode_(timer, NSRunLoopCommonModes)
    return timer


class _ClickThroughButton(NSButton):
    """Borderless button that responds to the first click on a non-key window."""

    def acceptsFirstMouse_(self, event):
        return True


class _ButtonTarget(NSObject):
    """Objective-C target for the "End now" button; forwards to a Python callable."""

    def initWithHandler_(self, handler):
        self = objc.super(_ButtonTarget, self).init()
        if self is None:
            return None
        self._handler = handler
        return self

    def endNow_(self, sender):
        try:
            self._handler()
        except Exception:
            # An exception escaping into AppKit would crash the app.
            log.exception("End now handler failed")


class _OverlayPanel(NSPanel):
    # Never become key/main: the user's frontmost app keeps keyboard focus.
    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False


def _label(font_size, weight, alpha):
    field = NSTextField.labelWithString_("")
    field.setFont_(NSFont.monospacedDigitSystemFontOfSize_weight_(font_size, weight))
    field.setTextColor_(NSColor.colorWithWhite_alpha_(1.0, alpha))
    field.setAlignment_(NSTextAlignmentCenter)
    field.setDrawsBackground_(False)
    field.setSelectable_(False)
    return field


class OverlayController:
    """Owns the per-screen panels and the countdown state machine.

    Phases: "lead_in" (5..1) -> "break" (20..0) -> "closing" -> done.
    `on_finish(ended_early)` is called exactly once when the overlay is gone.
    """

    def __init__(self, on_finish):
        self._on_finish = on_finish
        self._panels = []      # list of (panel, big_label, small_label, button)
        self._timer = None
        self._phase = None
        self._remaining = 0
        self._ended_early = False
        self._fade_target = 1.0
        self._deadline = 0.0   # time.monotonic() after which the overlay counts as stuck
        self._button_target = _ButtonTarget.alloc().initWithHandler_(self.end_now)

    # ------------------------------------------------------------------ public

    def is_showing(self):
        return self._phase is not None

    def show(self):
        if self._phase is not None:
            return
        self._phase = "lead_in"
        self._remaining = LEAD_IN_SECONDS
        self._deadline = (
            time.monotonic() + LEAD_IN_SECONDS + BREAK_SECONDS
            + FADE_IN_SECONDS + FADE_OUT_SECONDS + STUCK_GRACE_SECONDS
        )
        try:
            for screen in NSScreen.screens():
                self._panels.append(self._build_panel(screen))
            self._render()

            for panel, *_ in self._panels:
                panel.setAlphaValue_(0.0)
                panel.orderFrontRegardless()

            self._fade_target = 1.0
            NSAnimationContext.runAnimationGroup_completionHandler_(self._run_fade, None)
            self._timer = _schedule_repeating(1.0, self._timer_fired)
        except Exception:
            log.exception("Could not show overlay")
            self.force_close()

    def close_if_stuck(self):
        """Tear down an overlay that outlived its schedule. Returns True if it did.

        The app calls this from its own timer, so it still runs when the
        overlay's timer has died. Without it, a failure mid-break would leave
        a click-blocking window above every app with nothing to remove it.
        """
        if self._phase is None or time.monotonic() < self._deadline:
            return False
        log.error("Overlay stuck in phase %r past its deadline; forcing it closed", self._phase)
        self.force_close()
        return True

    def force_close(self):
        """Remove every panel immediately, no animation. Never raises."""
        self._stop_timer()
        if self._phase is None:
            return
        if self._phase != "closing":
            self._ended_early = True
        self._phase = "closing"
        self._teardown()

    def end_now(self):
        """"End now" was clicked: skip the rest of the break."""
        self.dismiss(ended_early=True)

    def dismiss(self, ended_early=True, animated=True):
        """Fade out and tear down. Safe to call repeatedly."""
        if self._phase in (None, "closing"):
            return
        self._phase = "closing"
        self._stop_timer()
        for _, _, _, button in self._panels:
            button.setEnabled_(False)

        self._ended_early = ended_early

        if not animated:
            self._teardown()
            return

        self._fade_target = 0.0
        NSAnimationContext.runAnimationGroup_completionHandler_(self._run_fade, self._teardown)

    # --------------------------------------------------------------- internals

    def _timer_fired(self, timer):
        try:
            self._tick()
        except Exception:
            log.exception("Overlay tick failed")
            self.force_close()

    def _tick(self):
        self._remaining -= 1
        if self._phase == "lead_in" and self._remaining <= 0:
            # "1" has been on screen for a full second: the break officially starts.
            self._phase = "break"
            self._remaining = BREAK_SECONDS
        elif self._phase == "break" and self._remaining <= 0:
            self._remaining = 0
            self._render()
            self.dismiss(ended_early=False)
            return
        self._render()

    def _run_fade(self, ctx):
        ctx.setDuration_(FADE_IN_SECONDS if self._fade_target > 0 else FADE_OUT_SECONDS)
        for panel, *_ in self._panels:
            panel.animator().setAlphaValue_(self._fade_target)

    def _teardown(self):
        if self._phase != "closing":
            return
        # Close every panel even if one fails, then always reset state, so a
        # single bad window can't leave the overlay half-open.
        for panel, *_ in self._panels:
            try:
                panel.orderOut_(None)
                panel.close()
            except Exception:
                log.exception("Could not close overlay panel")
        self._panels = []
        self._phase = None
        try:
            self._on_finish(self._ended_early)
        except Exception:
            log.exception("on_finish callback failed")

    def _render(self):
        text = LEAD_IN_TEXT if self._phase == "lead_in" else INSTRUCTION_TEXT
        big = str(self._remaining)
        for _, big_label, small_label, _ in self._panels:
            big_label.setStringValue_(big)
            small_label.setStringValue_(text)

    def _stop_timer(self):
        if self._timer is not None:
            try:
                self._timer.invalidate()
            except Exception:
                log.exception("Could not stop overlay timer")
            self._timer = None

    def _build_panel(self, screen):
        frame = screen.frame()
        panel = _OverlayPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        # PyObjC manages the lifetime; don't let -close release it underneath us.
        panel.setReleasedWhenClosed_(False)
        panel.setFrame_display_(frame, False)
        panel.setOpaque_(False)
        panel.setHasShadow_(False)
        panel.setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.04, BACKGROUND_ALPHA))
        # Above the menu bar, Dock and other apps' fullscreen windows.
        panel.setLevel_(NSScreenSaverWindowLevel)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorIgnoresCycle
        )
        panel.setHidesOnDeactivate_(False)   # NSPanel defaults to hiding when the app is inactive
        panel.setIgnoresMouseEvents_(False)  # swallow clicks instead of passing them through
        panel.setMovable_(False)

        w, h = frame.size.width, frame.size.height
        content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        panel.setContentView_(content)

        big_size = min(200.0, h * 0.22)
        big_h = big_size * 1.25
        big_y = h / 2 - big_h / 2 + 30
        big = _label(big_size, NSFontWeightLight, 0.95)
        big.setFrame_(NSMakeRect(0, big_y, w, big_h))
        content.addSubview_(big)

        small = _label(28.0, NSFontWeightRegular, 0.7)
        small.setFrame_(NSMakeRect(0, big_y - 44, w, 40))
        content.addSubview_(small)

        button = _ClickThroughButton.alloc().initWithFrame_(NSMakeRect(w - 140, 24, 116, 28))
        button.setBordered_(False)
        button.setAttributedTitle_(
            NSAttributedString.alloc().initWithString_attributes_(
                "End now",
                {
                    NSFontAttributeName: NSFont.systemFontOfSize_(13.0),
                    NSForegroundColorAttributeName: NSColor.colorWithWhite_alpha_(1.0, 0.4),
                },
            )
        )
        button.setTarget_(self._button_target)
        button.setAction_("endNow:")
        content.addSubview_(button)

        return (panel, big, small, button)
