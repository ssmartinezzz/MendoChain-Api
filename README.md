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

### Tests

```bash
SECRET_KEY=test DB_NAME=... DB_USER=... DB_PASSWORD=... python manage.py test
```

The Algorand calls are mocked, so tests never reach the network.

### Hyperledger Fabric network (optional)

`mendochain-network/crypto-config.yaml` describes the test network topology. Generate its certificates and keys locally with:

```bash
cryptogen generate --config=mendochain-network/crypto-config.yaml --output=mendochain-network/crypto-config
```

Generated key material is ignored by git and must never be committed.
