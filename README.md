# MendoChain API

Backend for MendoChain, a wine traceability platform that records each bottle's journey through the supply chain on the Algorand blockchain.

Built with Django REST Framework, JWT authentication and the Algorand Python SDK. The end-to-end suite lives in [MendoChainAutomatedTests](https://github.com/ssmartinezzz/MendoChainAutomatedTests).

## Features

- Wine and supply-chain entities exposed through a REST API with filtering and pagination
- JWT authentication with `djangorestframework-simplejwt`
- Traceability events written as Algorand TestNet transactions

## Getting started

Requires Python 3.12 and PostgreSQL.

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own values
python manage.py migrate
python manage.py runserver
```

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
SECRET_KEY=test LOG_LEVEL=WARNING DB_NAME=... DB_USER=... DB_PASSWORD=... python manage.py test
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
