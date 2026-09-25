# MendoChain API

Backend for MendoChain, a wine traceability platform. Wineries register lots of bottles and every movement along the supply chain goes through a **smart contract on Algorand** that enforces who may hold and move which bottles, so the history can be verified independently of this database.

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

The script only fills values missing from `.env` (random `SECRET_KEY` and `ACTOR_KEYS_SECRET`, `DEBUG=true` and local database settings); existing values are never overwritten. It skips the container when `DATABASE_URL` is set or `DB_HOST` is not local.

## API

Reads are public; writes need a JWT (`Authorization: Bearer <token>`) obtained from `/login`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/login` | Obtain access and refresh tokens |
| `GET` | `/auth/current_user` | Current user, including `is_staff` (`{"username": ""}` when anonymous) |
| `GET` | `/auth/users` | List users (admins only) |
| `POST` | `/auth/users` | Create a user (admins only; prefer `/api/admin/members`) |
| `GET` `PUT` `PATCH` `DELETE` | `/auth/users/<id>` | A user (the user themself or an admin) |
| `GET` | `/api/wine` | Active wines, paginated (`?page=`) |
| `POST` | `/api/wine` | Register a wine and its on-chain lot (winery actors; requires `total_quantity`) |
| `GET` | `/api/allwine` | Active wines, not paginated |
| `GET` | `/api/wine/<id>` | A wine, including retired ones |
| `PUT` | `/api/wine/<id>` | Update an active wine |
| `DELETE` | `/api/wine/<id>` | Retire a wine; on-chain lots only by their producer |
| `GET` | `/api/transaction` | Active movements, paginated |
| `POST` | `/api/transaction` | Transfer bottles to another actor through the contract (`wine`, `recipient`, `quantity >= 1`) |
| `GET` | `/api/transaction/<id>` | A movement, including retired ones |
| `DELETE` | `/api/transaction/<id>` | Retire a movement (soft delete) |
| `GET` | `/api/actors` | Active supply-chain actors: id, name, role, address (signed-in users) |
| `POST` | `/api/actors` | Make a user an actor: creates its custodial Algorand account and registers its role on chain (admins; `user`, `role` 1 winery, 2 distributor, 3 retailer) |
| `DELETE` | `/api/actors/<id>` | Revoke an actor's role on chain (admins) |
| `GET` | `/api/admin/members` | Every user with its actor and status (admins) |
| `POST` | `/api/admin/members` | Onboard a member: account + custodial actor + on-chain role in one step (admins; `email`, `password`, `first_name`, `last_name`, `role`) |

Movements cannot be edited: they mirror immutable on-chain transactions. Wines created before the contract are kept as read-only legacy records (no `total_quantity`, cannot move).

**Errors** always have the same shape, and every response carries an `X-Request-ID` header (send your own to correlate logs):

```json
{"error": {"code": "wine_not_found", "message": "Wine 7 does not exist.", "details": null}}
```

| Status | When |
|--------|------|
| 400 `invalid` | Input validation failed; `details` lists the fields |
| 401 | Missing credentials |
| 403 | Not allowed (`not_an_actor`, `actor_revoked`, `winery_only`, `producer_only`, or a permission failure) |
| 404 | Unknown resource (`wine_not_found`, `transaction_not_found`, `not_found`) |
| 409 | Conflict: a contract rule was rejected on chain (`insufficient_balance`, `unknown_recipient`, `unknown_sender`, `lot_retired`, `self_transfer`, ...), `legacy_wine`, `actor_already_registered`, `actor_already_revoked` or `member_already_exists`; nothing was stored |
| 502 `ledger_unavailable` | Algorand could not be reached; nothing was stored |

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
| `PRIVATE_KEY` | for the ledger | Admin account of the contract: deploys it, funds and registers actors. |
| `ALGORAND_APP_ID` | for the ledger | App id printed by `manage.py deploy_traceability`. |
| `ACTOR_KEYS_SECRET` | for the ledger | Fernet key that encrypts custodial actor keys at rest. Losing it makes actor accounts unusable; rotating it requires re-encrypting them. |
| `ALGOD_ADDRESS`, `ALGOD_TOKEN` | no | Algorand node. Defaults to the public TestNet node. |
| `LOG_LEVEL` | no | Level for the `api` loggers. Defaults to `INFO`. |

## Smart contract

`contracts/traceability/contract.py` is written in Algorand Python (ARC-4) and compiled to TEAL in `contracts/traceability/build/`. Each lot is a balance of bottles per actor; the contract enforces:

| Method | Caller | Rule |
|--------|--------|------|
| `register_actor(account, role)` | admin | role is winery, distributor or retailer |
| `revoke_actor(account)` | admin | the account had a role; afterwards it cannot register lots, send or receive |
| `register_lot(lot, total)` | winery | lot is new, `total > 0`; the winery receives every bottle |
| `transfer(lot, to, quantity)` | registered holder | lot active, `0 < quantity <= balance`, `to` is another registered actor |
| `retire_lot(lot)` | producing winery | no more transfers of that lot |

Every change emits an ARC-28 event, so the full history can be read from the chain. Actors use **custodial accounts**: the API generates one Algorand account per actor and stores its key encrypted with `ACTOR_KEYS_SECRET`; each operation is signed by the acting user's account, never by a shared server wallet.

### Run it locally

```bash
uvx algokit localnet start                      # Algorand LocalNet in Docker
uv run --group contracts pytest contracts       # contract unit tests + LocalNet tests
```

To point the API at LocalNet, set `ALGOD_ADDRESS=http://localhost:4001`, `ALGOD_TOKEN` to 64 `a` characters and a funded `PRIVATE_KEY`, then deploy (see below).

### Deploy and onboard actors

1. Fund the admin account (`PRIVATE_KEY`) on the target network (TestNet dispenser or LocalNet).
2. `uv run python manage.py deploy_traceability --funding 2` creates the app, funds it for box storage and prints `ALGORAND_APP_ID=...`; add it to the environment.
3. Create the first admin: `uv run python manage.py createsuperuser`.
4. Sign in to the web app as that admin and open **Admin** to onboard each winery, distributor and retailer (email, name, initial password, role). Each gets its custodial account and 0.3 ALGO from the contract admin for its minimum balance and fees. There is no public signup: only admins create accounts.
5. To remove a participant, **Revoke** it in the same panel. The role is removed on chain, the account can no longer operate, and its balances stay on chain as evidence. Revocation cannot be undone.

> Actors are registered in one specific deployment. If the contract is deployed again (new `ALGORAND_APP_ID`), existing actors are not registered in the new app and must be onboarded again.

Box storage costs `2500 + 400 * (key + value bytes)` microAlgos per box, locked in the app account; keep it funded as lots and holders grow.

To change the contract, edit `contract.py`, add tests in `contracts/tests/` and rebuild:

```bash
cd contracts/traceability && uv run --group contracts puyapy contract.py --out-dir build --output-arc56
```

## Architecture

The code is organized by domain, and the traceability domain is layered so business rules do not depend on HTTP or on Algorand.

```
contracts/
  traceability/      Algorand Python contract and its compiled TEAL / ARC-56 spec
  deploy.py          creates and funds the app
api/
  core/              error envelope, X-Request-ID middleware, pagination
  accounts/          users and JWT
  traceability/
    domain/          domain errors, roles and the LedgerGateway port
    application/     use cases (services) and read queries (selectors)
    infrastructure/  contract adapter implementing LedgerGateway, key vault for custodial keys
    interfaces/      input/output serializers, views, urls
```

| Decision | Why |
|----------|-----|
| Rules live in the contract, not only in the API | The chain rejects invalid movements even if the API has a bug. |
| Only the blockchain sits behind a port | It is the one external system; services use Django models directly. |
| `LEDGER_GATEWAY` setting selects the adapter | Tests swap in an in-memory fake without mocking the SDK. |
| Separate input and output serializers | Clients can never write server-owned fields such as `transaction_id`. |
| Soft deletes | Retired wines stay readable so movement history keeps resolving them. |

## Development

| Task | Command |
|------|---------|
| Run tests | `./setup.sh test` |
| Run tests against an existing database | `SECRET_KEY=test LOG_LEVEL=WARNING DB_NAME=... DB_USER=... DB_PASSWORD=... uv run python manage.py test` |
| Run contract tests | `uv run --group contracts pytest contracts` |
| Add a dependency | `uv add <package>` |
| Upgrade within allowed ranges | `uv lock --upgrade` |
| Any Django command | `uv run python manage.py <command>` |

Unit tests use an in-memory ledger. Tests marked for LocalNet run the compiled contract when `uvx algokit localnet start` is running and are skipped otherwise; no test reaches TestNet or MainNet.

## Deployment

The `Procfile` runs migrations on release and serves the app with gunicorn. The target platform needs:

- Python 3.12 (see `.python-version`).
- `SECRET_KEY`, `ALLOWED_HOSTS`, a database, `PRIVATE_KEY`, `ALGORAND_APP_ID` and `ACTOR_KEYS_SECRET`.
- A `requirements.txt` only if the platform cannot read `uv.lock`: `uv export --no-hashes --no-dev > requirements.txt`.

## Hyperledger Fabric network (optional)

`mendochain-network/crypto-config.yaml` describes a test network topology. Generate its certificates and keys locally with:

```bash
cryptogen generate --config=mendochain-network/crypto-config.yaml --output=mendochain-network/crypto-config
```

Generated key material is ignored by git and must never be committed.
