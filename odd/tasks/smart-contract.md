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
- [x] C4 Domain and ledger port: wine total and producer, movements with sender and recipient; `LedgerGateway` operations; Algorand contract adapter; fake ledger.
- [x] C5 API: endpoints and serializers for lots, transfers and actors.
- [x] C6 Frontend: total bottles on wine creation, recipient on movements.
- [x] C7 End-to-end check on LocalNet.

## Acceptance criteria
- Every rule above is rejected on chain when violated (unit tests) and surfaced by the API as a clear error.
- Full suites green; contract compiles.

## Progress
- C1: RED 16/17 (stub interface), GREEN 17/17. Compiled with `uv run --group contracts puyapy contract.py --out-dir build --output-arc56` (run in `contracts/traceability`). `.native` on ARC-4 ints is deprecated: use `.as_uint64()`. `algorand-python-testing` 1.1.0 fails to emit a single-field struct event, so `LotRetired` also carries the producer. Unit tests emulate the contract in Python; box references and MBR are only exercised on LocalNet (C2/C7).
- C2: RED (missing `contracts.deploy`), GREEN 19/19 including 2 LocalNet tests: the compiled TEAL enforces `insufficient balance` on a real AVM, box references are populated automatically by algokit-utils, and the app account is funded.
- C3: RED 9 (stubs: plaintext vault, NotImplemented service, conflict unmapped), GREEN 82/82. `Actor` model (migration 0006), `KeyVault` (Fernet, `ACTOR_KEYS_SECRET`), `register_actor` registers on the ledger before storing, `ConflictError` -> 409. `setup.sh` generates `ACTOR_KEYS_SECRET`.
- Pending: `.env.example` needs `ACTOR_KEYS_SECRET` and the app id (blocked by permission rules when the working directory is the repo).
- Note: running `./setup.sh test` in the real repo created a local `.env` from the template and stopped on the busy port 5432; use the runner with `DB_HOST=localhost DB_PORT=55432` instead.
- C4a (domain/services/port, fake ledger): RED 16/17, GREEN 17/17. Wine gets `total_quantity` and `producer`, movements get `sender`/`recipient` (migration 0007, nullable for legacy rows). `register_wine` and `retire_wine` call the ledger inside the DB transaction; `transfer_bottles` stores the movement only after the ledger accepts it. New errors: `ForbiddenError` (403: not_an_actor, winery_only, producer_only), `LegacyWine` and `LedgerRuleViolation` (409, code from the contract rule).
- C5 (API): RED 24/33, GREEN. Create/update input DTOs split (lot size fixed on chain), `recipient` on movements, `/api/actors` (list for signed-in users without email or keys, register for admins). Full suite 99/99.

- C4b (adapter): RED 7 (stub), GREEN. `AlgorandContractLedger` signs admin calls with PRIVATE_KEY and actor calls with their custodial key; `register_actor` funds and registers in one atomic group. Real LogicError messages include neighbouring assertions from the TEAL excerpt, so the rule is parsed from the header (`in transaction N: <rule>' at PC`) or the `<-- Error` line, never by substring search. `manage.py deploy_traceability --funding N` prints `ALGORAND_APP_ID`. Note adapter and `record()` removed; `ALGORAND_RECEIVER`/`WALLET_ADD` settings dropped. API 103/103 (LocalNet tests included), contracts 19/19.
- Machine restart stopped LocalNet and removed the `--rm` test DB; both recreated.

- C6 (Mendochain-Web, branch feat/traceability-contract): RED 11 + 1 (lot column), GREEN 39/39; build compiles. Total bottles on wine creation, recipient picker from /api/actors, lot size column, contract errors shown.
- C7 end-to-end on LocalNet: contract deployed with `manage.py deploy_traceability` (app 1087); admin registered a winery and a distributor through `POST /api/actors`; in the browser the winery created a 100-bottle wine and sent 30 to the distributor; sending 500 showed "Rejected by the traceability contract: insufficient balance." Read directly from the chain: winery 70, distributor 30, and the transfer was signed by the winery's custodial address.
- README (both repos) documents the contract, deployment, actor onboarding, errors and configuration.

## Pending
- `.env.example` (API): add `ALGORAND_APP_ID` and `ACTOR_KEYS_SECRET`, drop `WALLET_ADD` and `ALGORAND_RECEIVER`. Blocked by the user's permission rules while working inside the repo.
- Engram mirror (ambiguous project).

## Next step
Open PRs for both repositories.
