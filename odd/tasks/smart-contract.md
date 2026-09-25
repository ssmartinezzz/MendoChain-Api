# Traceability smart contract

## Objective
Replace note-only notarization with an Algorand smart contract that enforces supply-chain rules on chain: who may register lots, who holds how many bottles, and who may move them.

## Problem
Today each movement is a zero-amount payment from one server wallet with free text in the note. Nothing is validated on chain: quantities are unchecked, anyone can send notes to the receiver, records cannot be verified automatically, and a single server key signs everything.

## Decisions
- User (2026-09-24): level 2, a contract with rules.
- User (2026-09-24): custodial accounts. The backend creates one Algorand account per actor and stores its key encrypted; each movement is signed by its actor. Keeps the path open to self-custody wallets (level 3).
- Contract written in Algorand Python (ARC-4), compiled with `puyapy`, unit-tested with `algorand-python-testing`.
- Lots are fungible bottle balances per actor stored in boxes; history is emitted as ARC-28 events.
- Roles: winery (1), distributor (2), retailer (3). The admin (server account that creates the app) registers actors.
- The app account is funded by the admin to cover box minimum balance (`2500 + 400 * (key + value bytes)` microAlgos per box).
- Existing wines and movements stay as read-only legacy records (note-based).

## Contract rules
| Method | Caller | Rule |
|--------|--------|------|
| `register_actor(account, role)` | admin | role in {1, 2, 3} |
| `register_lot(lot, total)` | winery | lot is new, total > 0; caller receives the total |
| `transfer(lot, to, quantity)` | holder | lot active, 0 < quantity <= caller balance, `to` is a registered actor |
| `retire_lot(lot)` | producing winery | lot becomes inactive |

## TDD
- Mode: strict (source: global user configuration)
- Contract runner: `uv run --group contracts pytest contracts` (LocalNet tests skip unless `uvx algokit localnet start` is running)
- API runner: `./setup.sh test`

## Tasks
- [x] C1 Contract: roles, lots, balances, transfers, retirement, events; unit tests; compiles to TEAL + ARC-56 spec.
- [x] C2 Deployment: `contracts/deploy.py` creates the app from the ARC-56 spec and funds its account; verified on LocalNet. (Settings/management command for TestNet move to C4, with the adapter.)
- [x] C3 Custodial actor accounts: encrypted keys, role registration on chain, funding.
- [ ] C4 Domain and ledger port: wine total and producer, movements with sender and recipient; `LedgerGateway` operations; Algorand contract adapter; fake ledger.
- [ ] C5 API: endpoints and serializers for lots, transfers and actors.
- [ ] C6 Frontend: total bottles on wine creation, recipient on movements.
- [ ] C7 End-to-end check on LocalNet.

## Acceptance criteria
- Every rule above is rejected on chain when violated (unit tests) and surfaced by the API as a clear error.
- Full suites green; contract compiles.

## Progress
- C1: RED 16/17 (stub interface), GREEN 17/17. Compiled with `uv run --group contracts puyapy contract.py --out-dir build --output-arc56` (run in `contracts/traceability`). `.native` on ARC-4 ints is deprecated: use `.as_uint64()`. `algorand-python-testing` 1.1.0 fails to emit a single-field struct event, so `LotRetired` also carries the producer. Unit tests emulate the contract in Python; box references and MBR are only exercised on LocalNet (C2/C7).
- C2: RED (missing `contracts.deploy`), GREEN 19/19 including 2 LocalNet tests: the compiled TEAL enforces `insufficient balance` on a real AVM, box references are populated automatically by algokit-utils, and the app account is funded.
- C3: RED 9 (stubs: plaintext vault, NotImplemented service, conflict unmapped), GREEN 82/82. `Actor` model (migration 0006), `KeyVault` (Fernet, `ACTOR_KEYS_SECRET`), `register_actor` registers on the ledger before storing, `ConflictError` -> 409. `setup.sh` generates `ACTOR_KEYS_SECRET`.
- Pending: `.env.example` needs `ACTOR_KEYS_SECRET` and the app id (blocked by permission rules when the working directory is the repo).
- Note: running `./setup.sh test` in the real repo created a local `.env` from the template and stopped on the busy port 5432; use the runner with `DB_HOST=localhost DB_PORT=55432` instead.

## Next step
C4.
