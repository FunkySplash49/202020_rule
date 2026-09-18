# TwentyTwenty

A macOS menu bar app for the 20-20-20 rule: every 20 minutes, look at
something 20 feet away for 20 seconds.

When a break is due, a dark overlay fades in over every connected display. It
counts down 5 to 1, then shows a 20-second timer and "Look at something 20
feet away". When the timer reaches 0, the overlay fades out. It appears above
every app and on every Space, including apps in full screen.

## The menu

Click the eye icon in the menu bar.

- **Next break in 12m** is a status line showing time until the next break. It's greyed out because it isn't a button.
- **Skip next reminder** cancels the next break only, then switches itself off. It isn't an off switch, and it resets when you quit.
- **Quit** stops the app.

## During a break

- Clicks on the overlay do nothing, so you can't click past it.
- Typing still works. The overlay never takes keyboard focus, so keys go to
  the app you were using. There's no keyboard shortcut to dismiss it.
- **End now**, in the bottom-right corner, ends the break and starts a new 20 minutes.

If the overlay ever stays up after its timer should have finished, the app
removes it within about 10 seconds and logs an error.

## When the 20 minutes start over

- A break finishes, or you click "End now".
- A break is skipped with "Skip next reminder". The next break comes 40
  minutes after the previous one.
- The Mac wakes from sleep, or you unlock the screen.
- You come back after 5 minutes with no keyboard or mouse input.

The idle rule has a side effect. A long video watched without touching the
keyboard or mouse counts as time away, so breaks get postponed.

## Install and run from source

Needs Python 3.13. Tested only on macOS 26. The eye icon uses an SF Symbol,
which needs macOS 11 or later; older versions fall back to an emoji.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python twenty.py
```

`requirements.txt` pins every package to an exact version.

To test without waiting 20 minutes, set the timings in seconds:

```bash
TWENTY_INTERVAL=30 TWENTY_IDLE_RESET=600 .venv/bin/python twenty.py
```

`TWENTY_INTERVAL` accepts 5 to 86400 and `TWENTY_IDLE_RESET` accepts 30 to
86400. Any other value is logged and replaced with the default. The built
`.app` ignores both variables.

## Build the .app

```bash
.venv/bin/python setup.py py2app
```

This writes `dist/TwentyTwenty.app`, which runs without Python or the venv on
both Apple Silicon and Intel Macs. `setup.py py2app -A` makes a quicker
development build that links back to this folder, but that build can't be
copied to another Mac.

The app isn't code-signed. On another Mac, the first launch is blocked; open
it with right-click, then **Open**.

## Launch at login

Copy `TwentyTwenty.app` to `/Applications`. Then go to **System Settings >
General > Login Items & Extensions**, click **+** under "Open at Login", and
choose TwentyTwenty. It starts in the menu bar with no Dock icon and no window.

## Logs

The built app sends errors to the system log. Open Console.app and search
for "TwentyTwenty". When run from source, they print to the terminal.

## Security

The app makes no network requests and stores no data. It reads no files or
credentials. A 2026-09-18 audit against a 17-category checklist found four
issues, all now fixed:

- a failure mid-break could leave the screen covered
- unchecked timing values
- unpinned dependencies
- a missing `.gitignore`

Details are in [security/AUDIT_SUMMARY.md](security/AUDIT_SUMMARY.md).

Before a release build, check the dependencies for known vulnerabilities:

```bash
python3 -m venv /tmp/audit && /tmp/audit/bin/pip install pip-audit && /tmp/audit/bin/pip-audit -r requirements.txt
```

## Files

| File | What it does |
|---|---|
| `twenty.py` | Menu bar app: the 20-minute cycle, the menu, sleep, lock and idle handling |
| `overlay.py` | The overlay: one window per display, fades, countdown, "End now" |
| `setup.py` | py2app build settings |
| `requirements.txt` | Exact dependency versions |
| `security/` | Audit summary, reports and fix plans |
| `CLAUDE.md` | Design decisions and notes for working on the code |
