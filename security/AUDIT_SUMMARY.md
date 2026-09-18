# Security Audit Summary

Date: 2026-09-18

Audited against AGENTS.md, AI-CHECKLIST.md and manual-checklist.md.

TwentyTwenty is a local macOS menu bar app. It has no server, no network
access, no accounts, no database and no stored data. A search of the source
for network calls, deserialization, subprocesses, hashing, file writes and HTML
found none. The app's only inputs are two development-only environment
variables. Most checklist categories target web apps and don't apply here. The
table gives the reason for each; full reports and plans exist only for the
categories with findings.

## Results

| # | Category | Status | Report | Plan |
|---|----------|--------|--------|------|
| 1 | SECRETS_EXPOSURE | LOW, fixed | [report](reports/SECRETS_EXPOSURE_REPORT.md) | [plan](plans/SECRETS_EXPOSURE_PLAN.md) |
| 2 | DATABASE_ACCESS | N/A: no database, Supabase or Firebase | | |
| 3 | AUTH_MIDDLEWARE | N/A: no routes or endpoints | | |
| 4 | ACCESS_CONTROL | N/A: no resource IDs or users | | |
| 5 | FRONTEND_SECRETS | N/A: no browser frontend | | |
| 6 | SSRF | PASS: the app fetches no URLs | | |
| 7 | CSRF | N/A: no cookies, sessions or HTTP endpoints | | |
| 8 | SECURITY_HEADERS | N/A: no HTTP responses | | |
| 9 | CORS | N/A: no HTTP server | | |
| 10 | RATE_LIMITING | N/A: no login or registration | | |
| 11 | SQL_INJECTION | N/A: no SQL anywhere | | |
| 12 | XSS | PASS: fixed strings in NSTextField, no HTML or web views | | |
| 13 | PAYMENT_WEBHOOKS | N/A: no payments | | |
| 14 | FILE_UPLOADS | N/A: no uploads; the app reads and writes no files | | |
| 15 | ERROR_HANDLING | HIGH, fixed | [report](reports/ERROR_HANDLING_REPORT.md) | [plan](plans/ERROR_HANDLING_PLAN.md) |
| 16 | PASSWORD_HASHING | N/A: no passwords | | |
| 17 | DEPENDENCIES | MEDIUM, fixed | [report](reports/DEPENDENCIES_REPORT.md) | [plan](plans/DEPENDENCIES_PLAN.md) |
| + | INPUT_VALIDATION (AGENTS.md rule) | MEDIUM, fixed | [report](reports/INPUT_VALIDATION_REPORT.md) | [plan](plans/INPUT_VALIDATION_PLAN.md) |

## Critical issues

None open. The most serious finding was ERROR_HANDLING, rated HIGH: an
exception during a break could leave a click-blocking overlay above every app
with nothing to remove it. Overlay callbacks now catch and log errors and close
the overlay. A watchdog on the app's own timer removes any overlay that
outlives its schedule. Both paths were tested by breaking the overlay on
purpose.

## Remaining manual verification

- After a day of use, check Console.app (filter "TwentyTwenty") for ERROR lines.
- With an overlay up, press Cmd+Opt+Esc and note whether Force Quit appears above it.
- After `git init`, confirm `git status` doesn't list `.venv/`, `build/` or `dist/`.
- Before publishing the repo, run `gitleaks detect --source . --verbose`.
- Before each release build, run `pip-audit -r requirements.txt` from a throwaway venv.
