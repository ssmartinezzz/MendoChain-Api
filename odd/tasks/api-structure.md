# API structure

## Objective
Organize the API by domain with thin views, explicit input/output serializers, a service layer, a port for the blockchain, and consistent cross-cutting concerns (errors, request tracing).

## Problem
- Views mix HTTP, validation and business rules; `WineApiView.post` and `TransactionApiView.post` are dead code, `AllWineList` accepts POST.
- One serializer per model serves both input and output, so writable fields had to be patched with `read_only_fields`.
- The Algorand call lives in a serializer with node, receiver and fee hardcoded; it can only be tested by mocking the SDK.
- Error bodies differ per endpoint and requests cannot be traced in logs.

## Decisions
- User (2026-09-24): pragmatic hexagonal. Only the blockchain goes behind a port (`LedgerGateway`); services use Django models directly. No domain entities or repositories.
- Screaming layout: `api/core`, `api/accounts` (was `api/auth`), `api/traceability` (was `api/backend`). The traceability app keeps label `backend`, so tables and migrations are unchanged.
- URLs and success response bodies stay the same. Error bodies change to `{"error": {"code", "message", "details"}}` (frontend only logs errors).
- The ledger adapter is selected by the `LEDGER_GATEWAY` setting so tests swap in a fake without patching the SDK.
- Environment names `PRIVATE_KEY` and `WALLET_ADD` stay; node address, token and receiver become configurable with the current values as defaults.

## Target layout
```
api/
  core/            exceptions.py, middleware.py, pagination.py
  accounts/        (was api/auth)
  traceability/
    domain/        errors.py, ports.py
    application/   services.py, selectors.py
    infrastructure/ algorand.py, ledger.py
    interfaces/    serializers.py, views.py, urls.py
    models.py, migrations/
```

## TDD
- Mode: strict (source: global user configuration)
- Runner (Python 3.12 venv): `DB_NAME=mendochain DB_USER=test DB_PASSWORD=test DB_PORT=55432 SECRET_KEY=test LOG_LEVEL=WARNING venv/bin/python manage.py test`
- Moves (S1) are refactors: the existing suite is the safety net, no new RED expected.

## Tasks
- [x] S1 Move `api/backend` -> `api/traceability` (label `backend`) and `api/auth` -> `api/accounts`; suite green, no migrations.
- [x] S2 `core/exceptions.py`: one error envelope for DRF errors, 404 and domain errors.
- [x] S3 `core/middleware.py`: `X-Request-ID` (accept safe incoming ids, otherwise generate), request log line with status and latency; header exposed through CORS.
- [ ] S4 `LedgerGateway` port + `AlgorandLedger` adapter configured from settings; `LEDGER_GATEWAY` setting selects it.
- [ ] S5 Service layer and selectors; input/output serializers; thin views; remove dead code and POST on `allwine`.

## Acceptance criteria
- Full suite green; `check` clean; `makemigrations --check` no changes.
- Existing URL paths and success payloads unchanged.

## Progress
- S1: `git mv` of both apps; empty admin/models boilerplate removed. 39/39 OK, `makemigrations --check` no changes (label `backend` kept).
- S2: RED 7/7, GREEN. `api/core/errors.py` (DomainError, NotFoundError, UnavailableError) + `api/core/exceptions.py` handler; `handler404`/`handler500` return JSON. 46/46 OK.
- S3: RED 7/7, GREEN. `RequestIdMiddleware` first in the chain; `CORS_EXPOSE_HEADERS`; `LOGGING` for `api` loggers with `LOG_LEVEL`. Test runner now uses `LOG_LEVEL=WARNING`. 51/51 OK.

## Next step
S4.
