# Dependencies Fix Plan

## Changes

- `README.md`: install with `pip install -r requirements.txt` instead of
  naming packages loosely.

## New files

- `requirements.txt`: every package in the build environment, pinned with
  `==` (from `pip freeze --all`, minus pip itself).

## Verification goals

- [x] Every line in `requirements.txt` uses `==`. No `^`, `~`, `>=` or unpinned names.
- [x] Every package exists on PyPI with years of release history (see report table).
- [x] `pip-audit -r requirements.txt` reports "No known vulnerabilities found".
- [x] pip-audit ran from a separate virtualenv, so it isn't in the app's pins.

## Manual verification (for the human)

- Before each release build, run this from a throwaway venv:
  `pip install pip-audit && pip-audit -r requirements.txt`
- When upgrading, change the pins on purpose, rebuild, and run the app for a
  cycle before shipping.
