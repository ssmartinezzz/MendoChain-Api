# MendoChain API

Backend for MendoChain, a wine traceability platform that records each bottle's journey through the supply chain on the Algorand blockchain.

Built with Django REST Framework, JWT authentication and the Algorand Python SDK. The end-to-end suite lives in [MendoChainAutomatedTests](https://github.com/ssmartinezzz/MendoChainAutomatedTests).

## Features

- Wine and supply-chain entities exposed through a REST API with filtering and pagination
- JWT authentication with `djangorestframework-simplejwt`
- Traceability events written as Algorand TestNet transactions

## Getting started

Requires [uv](https://docs.astral.sh/uv/) and Docker (for the local PostgreSQL).

```bash
./setup.sh        # create .env, start PostgreSQL, install Python 3.12 + dependencies, migrate
./setup.sh run    # same, then start the development server on http://127.0.0.1:8000
./setup.sh test   # same, then run the test suite
./setup.sh db-stop
```

The script only fills missing values in `.env` (a random `SECRET_KEY`, `DEBUG=true` and local database settings); existing values are kept. If `DATABASE_URL` is set or `DB_HOST` is not local, it skips the PostgreSQL container.

Setup output is also written to `.setup.log`. If the database port is busy, the script stops and suggests a free `DB_PORT`; if the container runs without its port mapping, it is recreated on the same volume, so data is kept.

Dependencies are managed with uv: add one with `uv add <package>`, and upgrade within the allowed ranges with `uv lock --upgrade`. For platforms that need a `requirements.txt`, generate it with `uv export --no-hashes --no-dev > requirements.txt`.

### Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | yes | Django secret key. The app refuses to start without it. |
| `ALLOWED_HOSTS` | in production | Comma-separated host names. |
| `DEBUG` | no | `true` to enable debug mode. Off by default. |
| `DATABASE_URL` | no | Database URL. Takes precedence over the `DB_*` variables. |
| `DATABASE_SSL_REQUIRE` | no | Require SSL for `DATABASE_URL` connections. Defaults to `true`. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | without `DATABASE_URL` | PostgreSQL connection. `DB_HOST` defaults to `localhost`. |
| `PRIVATE_KEY`, `WALLET_ADD` | for transactions | Algorand account used to sign traceability transactions. |
| `ALGOD_ADDRESS`, `ALGOD_TOKEN` | no | Algorand node. Defaults to the public TestNet node. |
| `ALGORAND_RECEIVER` | no | Address that receives the zero-amount traceability payments. |
| `LOG_LEVEL` | no | Level for the `api` loggers. Defaults to `INFO`. |

### Tests

```bash
./setup.sh test
# or, against an existing database:
SECRET_KEY=test LOG_LEVEL=WARNING DB_NAME=... DB_USER=... DB_PASSWORD=... uv run python manage.py test
```

Tests replace the ledger with an in-memory fake (`LEDGER_GATEWAY`), so they never reach the network.

## Project layout

```
api/
  core/            error envelope, request id middleware, pagination
  accounts/        users and JWT
  traceability/
    domain/        domain errors and the LedgerGateway port
    application/   use cases (services) and read queries (selectors)
    infrastructure/ Algorand adapter
    interfaces/    input/output serializers, views, urls
```

Errors always use `{"error": {"code", "message", "details"}}`, and every response carries an `X-Request-ID` header.

### Hyperledger Fabric network (optional)

`mendochain-network/crypto-config.yaml` describes the test network topology. Generate its certificates and keys locally with:

```bash
cryptogen generate --config=mendochain-network/crypto-config.yaml --output=mendochain-network/crypto-config
```

Generated key material is ignored by git and must never be committed.
