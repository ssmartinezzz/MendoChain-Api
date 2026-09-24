# Security hardening

## Objective
Close the access-control and configuration holes in the API before any other maintenance work.

## Problem
- `GET /auth/users` lists every user (with emails) to anonymous callers.
- `/auth/users/<pk>` lets any authenticated user update or delete any other user.
- `DEBUG = True` is hardcoded and `SECRET_KEY` falls back to a committed default.
- The app cannot even import: `algosdk.future` was removed in py-algorand-sdk 2.x and the dependency is unpinned.

## Scope
In: user endpoints permissions, DEBUG/SECRET_KEY/ALLOWED_HOSTS from environment, minimal algosdk import fix needed to run tests.
Out (later phases): dependency upgrades, wine/transaction logic bugs, blockchain service refactor.

## TDD
- Mode: strict (source: global user configuration)
- Runner: `DB_NAME=mendochain DB_USER=test DB_PASSWORD=test DB_PORT=55432 SECRET_KEY=test venv/bin/python manage.py test`
- Test DB: throwaway `postgres:16-alpine` container `mendochain-test-db` on port 55432.

## Tasks
- [x] T0 Make the app importable: `from algosdk import transaction`, pin `py-algorand-sdk==2.6.1`.
- [x] T1 `GET /auth/users` restricted to admin users; `POST /auth/users` keeps its current behavior (authenticated only).
- [x] T2 `/auth/users/<pk>`: retrieve/update/delete only for the user themself or an admin.
- [x] T3 `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` read from environment; `DEBUG` defaults to off, no committed secret fallback.
- [x] T4 Decision (user): any registered user may create wines and transactions. Matches current behavior; locked with characterization tests (blockchain mocked). Signup stays authenticated-only.

## Acceptance criteria
- Tests for T1–T3 observed RED before implementation, GREEN after.
- Full suite passes.

## Progress
- Environment set up locally (Python 3.9 venv, psycopg2-binary, django-heroku --no-deps, setuptools<70) without changing `requirements.txt` beyond T0.
- T0: import fixed; suite loads (0 tests, OK).
- T1/T2: RED observed (6 permission failures), GREEN 9/9 after `IsSelfOrAdmin` + admin-only list.
- Finding: anonymous signup was already blocked (401) by the global `IsAuthenticatedOrReadOnly`; behavior preserved, decision moved to T4.
- T3: RED observed (4/5), GREEN after env-driven settings. `django_heroku.settings()` was overriding ALLOWED_HOSTS with `['*']`; now called with `allowed_hosts=False`.
- Full suite: 14/14 OK. `check --deploy`: remaining warnings are HTTPS/HSTS/cookie flags (deployment-dependent) and ALLOWED_HOSTS empty without env.
- Pending: `.env.example` must document `DEBUG` and `ALLOWED_HOSTS` (file not readable from this session). Engram mirror pending (ambiguous project).

- T4: no code change needed; 5 characterization tests pass on first run (no RED expected: behavior already existed). Full suite 19/19 OK.

## Next step
Commit this slice, then phase 2: dependency upgrades.
