# Secrets Exposure Fix Plan

## Changes

None to source files.

## New files

- `.gitignore`: ignores `.env` and `.env.*` (but keeps `.env.example`),
  `.venv/`, `build/`, `dist/`, `__pycache__/`, `*.pyc` and `.DS_Store`.

No `.env.example` was added. The app reads no configuration file, and an empty
example would suggest otherwise.

## Verification goals

- [x] The secret-pattern search over all source files returns nothing.
- [x] `.gitignore` lists `.env`.
- [x] No environment variable holds a secret. The only two are timing values
      for development.
- [ ] `git ls-files .env` returns nothing (not applicable yet, because the
      project isn't a git repository).

## Manual verification (for the human)

- After `git init`, run `git status` and check that `.venv/`, `build/` and
  `dist/` don't appear.
- Before pushing anywhere public, run `gitleaks detect --source . --verbose`.
