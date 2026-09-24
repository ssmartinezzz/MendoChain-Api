# Dependency upgrade

## Objective
Bring the project to supported versions so it installs and runs on a current Python without workarounds.

## Problem
- Pinned stack is from 2021 and out of support (Django 3.1, cryptography 3.4, urllib3 1.26, ...).
- `django-heroku` is abandoned and forces a source build of `psycopg2`.
- `requirements.txt` pins transitive and unused packages (`PyMySQL`, `requests`, `pytz`, `tzlocal`, `six`, ...).
- Local setup needed workarounds: Python 3.9, `psycopg2-binary`, `django-heroku --no-deps`, `setuptools<70`.

## Target
Python 3.12, Django 5.2 LTS (supported until April 2028), latest compatible DRF, simplejwt, django-cors-headers, whitenoise, gunicorn, psycopg 3, dj-database-url, python-dotenv, py-algorand-sdk.

## Scope
In: `requirements.txt`, settings changes required by the upgrade, removal of `django-heroku` and `pymysql`.
Out: wine/transaction logic bugs, blockchain service refactor.

## TDD
- Mode: strict (source: global user configuration)
- Runner (Python 3.12 venv): `DB_NAME=mendochain DB_USER=test DB_PASSWORD=test DB_PORT=55432 SECRET_KEY=test venv/bin/python manage.py test`
- Test DB: throwaway `postgres:16-alpine` container `mendochain-test-db` on port 55432.

## Tasks
- [x] D1 Replace `django-heroku` with explicit config: `DATABASE_URL` via dj-database-url (fallback to `DB_*` vars), whitenoise middleware and static storage. Tests for database config.
- [x] D2 Remove the unused `pymysql` initialization and package.
- [x] D3 Upgrade to the target stack on Python 3.12; `requirements.txt` lists only direct dependencies, pinned.
- [x] D4 Fix deprecations raised by Django 5.2 (`STORAGES`, `DEFAULT_AUTO_FIELD`, CORS setting names, `USE_L10N`); no new migrations generated unintentionally.

## Acceptance criteria
- Full suite green on Python 3.12 with a clean install from `requirements.txt`.
- `manage.py check` clean; `makemigrations --check` reports no changes.

## Progress
- D1: RED observed (3/9: DATABASE_URL engine alias, DB_HOST hardcoded, whitenoise order). dj-database-url 3.x needs Python >= 3.10, so D1 was completed together with D3.
- D2: `pymysql.install_as_MySQLdb()` removed from `api/__init__.py`; package dropped.
- D3: fresh venv on Python 3.12 from the new `requirements.txt` (10 direct pins). Required fix: app label `api.auth` -> `api_auth` (Django 3.2+ requires a valid identifier; the app has no models or migrations). Suite 23/23 OK.
- D4: found that Django 5.1+ silently ignores `STATICFILES_STORAGE` (runtime storage was plain `StaticFilesStorage`); RED observed, fixed with `STORAGES`. `CORS_ORIGIN_WHITELIST` renamed to `CORS_ALLOWED_ORIGINS` behind characterization tests. `DEFAULT_AUTO_FIELD = AutoField` keeps existing keys (no migration). Removed nonexistent `STATICFILES_DIRS` and `USE_L10N`.
- Final: 26/26 OK; `check` (with DeprecationWarning as error) clean; `makemigrations --check` no changes; `collectstatic` OK.
- README documents Python 3.12, environment variables and tests.

## Next step
Phase 3: wine/transaction logic bugs with tests.
