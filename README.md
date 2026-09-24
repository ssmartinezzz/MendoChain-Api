# MendoChain API

Backend for MendoChain, a wine traceability platform. Each movement of a wine through the supply chain is recorded as a transaction on the Algorand blockchain, so its history can be verified independently of this database.

Built with Django 5.2 LTS, Django REST Framework, JWT authentication and the Algorand Python SDK. The frontend is [Mendochain-Web](https://github.com/ssmartinezzz/Mendochain-Web) and the end-to-end suite lives in [MendoChainAutomatedTests](https://github.com/ssmartinezzz/MendoChainAutomatedTests).

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and Docker.

```bash
./setup.sh run
```

This creates `.env`, starts PostgreSQL in Docker, installs Python 3.12 and the dependencies, applies migrations and serves the API on http://127.0.0.1:8000. Check it with:

```bash
curl http://127.0.0.1:8000/api/hello_world
```

| Command | What it does |
|---------|--------------|
| `./setup.sh` | Prepare everything without starting the server |
| `./setup.sh run` | Prepare, then start the development server |
| `./setup.sh test` | Prepare, then run the test suite |
| `./setup.sh db-stop` | Stop the PostgreSQL container |

> **Port 5432 already in use?** The script stops and suggests a free port. Set it as `DB_PORT` in `.env` and run it again. The full output of every run is in `.setup.log`.

The script only fills values missing from `.env` (a random `SECRET_KEY`, `DEBUG=true` and local database settings); existing values are never overwritten. It skips the container when `DATABASE_URL` is set or `DB_HOST` is not local.

## API

Reads are public; writes need a JWT (`Authorization: Bearer <token>`) obtained from `/login`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/login` | Obtain access and refresh tokens |
| `GET` | `/auth/current_user` | Current user (`{"username": ""}` when anonymous) |
| `GET` | `/auth/users` | List users (admins only) |
| `POST` | `/auth/users` | Create a user (authenticated users) |
| `GET` `PUT` `PATCH` `DELETE` | `/auth/users/<id>` | A user (the user themself or an admin) |
| `GET` | `/api/wine` | Active wines, paginated (`?page=`) |
| `POST` | `/api/wine` | Register a wine |
| `GET` | `/api/allwine` | Active wines, not paginated |
| `GET` | `/api/wine/<id>` | A wine, including retired ones |
| `PUT` | `/api/wine/<id>` | Update an active wine |
| `DELETE` | `/api/wine/<id>` | Retire a wine (soft delete) |
| `GET` | `/api/transaction` | Active movements, paginated |
| `POST` | `/api/transaction` | Record a movement on Algorand (`wine`, `quantity >= 1`) |
| `GET` | `/api/transaction/<id>` | A movement, including retired ones |
| `DELETE` | `/api/transaction/<id>` | Retire a movement (soft delete) |

Movements cannot be edited: they mirror immutable on-chain transactions.

**Errors** always have the same shape, and every response carries an `X-Request-ID` header (send your own to correlate logs):

```json
{"error": {"code": "wine_not_found", "message": "Wine 7 does not exist.", "details": null}}
```

| Status | When |
|--------|------|
| 400 `invalid` | Input validation failed; `details` lists the fields |
| 401 / 403 | Missing credentials / not allowed |
| 404 | Unknown resource (`wine_not_found`, `transaction_not_found`, `not_found`) |
| 502 `ledger_unavailable` | Algorand rejected or did not receive the movement; nothing was stored |

## Configuration

Set these in `.env` locally or in the environment when deployed.

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | yes | Django secret key. The app refuses to start without it. |
| `ALLOWED_HOSTS` | in production | Comma-separated host names. |
| `DEBUG` | no | `true` to enable debug mode. Off by default. |
| `DATABASE_URL` | no | Database URL. Takes precedence over the `DB_*` variables. |
| `DATABASE_SSL_REQUIRE` | no | Require SSL for `DATABASE_URL`. Defaults to `true`. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | without `DATABASE_URL` | PostgreSQL connection. `DB_HOST` defaults to `localhost`. |
| `PRIVATE_KEY`, `WALLET_ADD` | to record movements | Algorand account that signs the transactions. |
| `ALGOD_ADDRESS`, `ALGOD_TOKEN` | no | Algorand node. Defaults to the public TestNet node. |
| `ALGORAND_RECEIVER` | no | Address that receives the zero-amount traceability payments. |
| `LOG_LEVEL` | no | Level for the `api` loggers. Defaults to `INFO`. |

## Architecture

The code is organized by domain, and the traceability domain is layered so business rules do not depend on HTTP or on Algorand.

```
api/
  core/              error envelope, X-Request-ID middleware, pagination
  accounts/          users and JWT
  traceability/
    domain/          domain errors and the LedgerGateway port
    application/     use cases (services) and read queries (selectors)
    infrastructure/  Algorand adapter implementing LedgerGateway
    interfaces/      input/output serializers, views, urls
```

| Decision | Why |
|----------|-----|
| Only the blockchain sits behind a port | It is the one external system; services use Django models directly. |
| `LEDGER_GATEWAY` setting selects the adapter | Tests swap in an in-memory fake without mocking the SDK. |
| Separate input and output serializers | Clients can never write server-owned fields such as `transaction_id`. |
| Soft deletes | Retired wines stay readable so movement history keeps resolving them. |

## Development

| Task | Command |
|------|---------|
| Run tests | `./setup.sh test` |
| Run tests against an existing database | `SECRET_KEY=test LOG_LEVEL=WARNING DB_NAME=... DB_USER=... DB_PASSWORD=... uv run python manage.py test` |
| Add a dependency | `uv add <package>` |
| Upgrade within allowed ranges | `uv lock --upgrade` |
| Any Django command | `uv run python manage.py <command>` |

Tests never reach the Algorand network.

## Deployment

The `Procfile` runs migrations on release and serves the app with gunicorn. The target platform needs:

- Python 3.12 (see `.python-version`).
- `SECRET_KEY`, `ALLOWED_HOSTS`, a database and the Algorand account variables.
- A `requirements.txt` only if the platform cannot read `uv.lock`: `uv export --no-hashes --no-dev > requirements.txt`.

## Hyperledger Fabric network (optional)

`mendochain-network/crypto-config.yaml` describes a test network topology. Generate its certificates and keys locally with:

```bash
cryptogen generate --config=mendochain-network/crypto-config.yaml --output=mendochain-network/crypto-config
```

Generated key material is ignored by git and must never be committed.
