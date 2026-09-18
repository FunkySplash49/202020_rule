# Input Validation Security Report

## Status: MEDIUM (fixed, verified)

This is not one of the 17 checklist categories. It comes from the AGENTS.md
rule "ALL user input MUST be validated". The app's only external input is two
environment variables.

## Findings

`twenty.py` read both variables with a bare `int()` and no limits:

```python
BREAK_INTERVAL_SECONDS = int(os.environ.get("TWENTY_INTERVAL", 20 * 60))
IDLE_RESET_SECONDS = int(os.environ.get("TWENTY_IDLE_RESET", 5 * 60))
```

- A non-number (`TWENTY_INTERVAL=abc`) raised `ValueError` at import, so the app
  never started.
- `TWENTY_INTERVAL=0` or a negative value made every break due immediately.
  After "End now" the cycle reset to "now + 0", and a new overlay appeared on
  the next one-second tick.
- A tiny `TWENTY_IDLE_RESET` would treat any pause in typing as time away and
  keep postponing breaks.
- The packaged `.app` honored both variables.

## What's at risk

With `TWENTY_INTERVAL=0`, the screen is covered almost continuously and clicks
are blocked, which makes the Mac close to unusable until the app is killed.
Getting this into the app's environment takes local access (`launchctl setenv`
or a modified launch). So the realistic cause is a typo during development,
or a prank from someone at your keyboard, not a remote attacker.

## What's already secure

- The app reads no files, no network data, no URLs and no clipboard. These two
  variables are its whole input surface.
- The overlay's text is fixed strings drawn in NSTextField. Nothing is parsed
  as HTML or markup.

## Recommendations

1. Validate both values as whole numbers inside a range. Reject anything else
   and fall back to the default.
2. Don't read them at all in the packaged app.

## Verification results

All goals in plans/INPUT_VALIDATION_PLAN.md pass.
