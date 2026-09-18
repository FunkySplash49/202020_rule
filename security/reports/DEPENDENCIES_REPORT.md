# Dependencies Security Report

## Status: MEDIUM (fixed, verified)

## Findings

- There was no `requirements.txt` or lock file. Versions came from whatever
  `pip install rumps pyobjc-framework-Cocoa pyobjc-framework-Quartz py2app`
  resolved on the day, so two builds could bundle different code.
- `pip-audit` had never been run.

Packages in the build (all now pinned in `requirements.txt`):

| Package | Version | First on PyPI | Releases | Maintainer |
|---|---|---|---|---|
| rumps | 0.4.0 | 2014 | 8 | Jared Suttles |
| pyobjc-core | 12.2.2 | 2009 | 69 | Ronald Oussoren |
| pyobjc-framework-Cocoa | 12.2.2 | 2009 | 68 | Ronald Oussoren |
| pyobjc-framework-Quartz | 12.2.2 | 2009 | 68 | Ronald Oussoren |
| py2app | 0.28.10 | 2006 | 52 | Ronald Oussoren |
| altgraph | 0.17.5 | 2005 | 22 | Ronald Oussoren |
| macholib | 1.16.4 | 2005 | 27 | Ronald Oussoren |
| modulegraph | 0.19.7 | 2005 | 29 | Ronald Oussoren |
| packaging | 26.3 | 2014 | 54 | PyPA |
| setuptools | 84.0.0 | 2006 | 625 | PyPA |

None of them shows the checklist's red flags: none is new, none has a name that
imitates a popular package, and none is an unknown one-off upload.

## What's at risk

Without pins, a malicious or broken release of any of these would go into the
next `.app` build unnoticed. That includes py2app's helpers, which run at
build time.

## What's already secure

- `pip-audit -r requirements.txt` reports no known vulnerabilities (run
  2026-09-18).
- The dependency list is short and nearly all of it comes from one
  long-standing maintainer (PyObjC/py2app) or the PyPA.

## Recommendations

1. Keep `requirements.txt` as the exact, complete pin list. It doubles as the
   lock file.
2. Re-run `pip-audit` before each release build.
3. Watch `rumps`: 0.4.0 is its latest release and the project sees little
   activity. It has no known vulnerabilities. If it breaks on a future macOS,
   replace it with a small NSStatusItem wrapper.

## Verification results

All goals in plans/DEPENDENCIES_PLAN.md pass.
