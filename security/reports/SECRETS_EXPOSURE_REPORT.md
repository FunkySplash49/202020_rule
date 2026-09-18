# Secrets Exposure Security Report

## Status: LOW (fixed, verified)

## Findings

- No secrets anywhere. A search of `twenty.py`, `overlay.py` and `setup.py` for
  `sk_live_`, `sk_test_`, `AKIA`, `password =`, `secret =`, `token =` and
  `Bearer` returns nothing. The app uses no API, account or credential.
- No `.env` file exists and the code never loads one.
- There was no `.gitignore`. The project isn't a git repository yet, but the
  first `git add .` would have committed `.venv/`, `build/` and a 66 MB
  `dist/TwentyTwenty.app`, and any `.env` added later.
- `setup.py` uses the placeholder bundle ID `com.example.twentytwenty`. That
  isn't a secret, but change it before signing or distributing.

## What's at risk

Nothing leaks today. The missing `.gitignore` would matter the day someone adds
a signing credential or `.env` and commits the whole folder.

## What's already secure

- The app has no credentials to protect.
- Nothing ships to a browser, so the NEXT_PUBLIC_/VITE_/REACT_APP_ checks don't apply.

## Recommendations

1. Add a `.gitignore` covering `.env*` (except `.env.example`), `.venv/`,
   `build/`, `dist/` and Python/macOS clutter before the first commit.
2. When code signing is added, keep the certificate in the login keychain and
   the notarization password in `xcrun notarytool store-credentials`, never in
   the repo.

## Verification results

All goals in plans/SECRETS_EXPOSURE_PLAN.md pass.
