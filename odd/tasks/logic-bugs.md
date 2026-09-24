# Logic bugs in wines and transactions

## Objective
Make the wine and transaction endpoints behave as their HTTP verbs promise, and never lose track of an on-chain transaction.

## Problem
- `PUT /api/wine/<pk>` and `PUT /api/transaction/<pk>` hide the record (`visibility = 0`); the frontend uses PUT as its delete button, so records cannot be edited.
- Wine update ignores `brand_name`; `visibility` is writable by clients through POST/PUT.
- `GET /api/wine/<pk>` returns 200 with empty data when the wine does not exist.
- Transaction update returns 201 and allows changing fields that mirror an immutable on-chain record.
- If submission to Algorand fails with an exception the API returns 500; if the transaction is submitted but confirmation times out, it is on chain but never recorded.

## Decisions
- User (2026-09-24): do the correct API change now; the frontend (`Mendochain-Web`) is updated afterwards.
- Soft delete moves to `DELETE` (204). Soft-deleted records stay retrievable by id so transaction history keeps resolving its wine.
- Transactions are immutable once recorded: `PUT` returns 405.
- A submitted but unconfirmed transaction is recorded with its id; a failed submission records nothing and returns 502.

## Scope
In: `api/backend/views.py`, `api/backend/serializers.py`, `api/backend/blockchain.py` error handling.
Out: blockchain service refactor (phase 4), frontend changes, numeric field types.

## TDD
- Mode: strict (source: global user configuration)
- Runner (Python 3.12 venv): `DB_NAME=mendochain DB_USER=test DB_PASSWORD=test DB_PORT=55432 SECRET_KEY=test venv/bin/python manage.py test`

## Tasks
- [x] B1 Wine: `PUT` updates every field (including `brand_name`) and keeps the wine visible; `DELETE` soft-deletes (204); `visibility` is read-only; PUT/DELETE on missing or deleted wines return 404.
- [x] B2 `GET /api/wine/<pk>` returns 404 for a missing wine.
- [x] B3 Transaction: `PUT` returns 405; `DELETE` soft-deletes (204); `transaction_id` and `visibility` are read-only.
- [x] B4 Blockchain errors: submission failure -> 502 and no record; confirmation timeout after submission -> record the transaction id.

## Acceptance criteria
- RED observed for each task before implementation; full suite green.

## Progress
- RED observed: 9 failures + 1 error across B1-B4. Two tests passed before implementation and stay as safety nets (soft-deleted wine retrievable by id; POST ignores a client-supplied `transaction_id`).
- B1/B2: `WineApiView` uses `get_object_or_404`; PUT/DELETE only on visible wines; `WineSerializer` drops its custom `update` (default updates every field) and makes `visibility` read-only.
- B3: `TransactionApiView.put` removed (405); `DELETE` soft-deletes; `transaction_id` and `visibility` read-only.
- B4: `blockchain.py` raises `BlockchainError` when submission fails (mapped to 502 `BlockchainUnavailable`); confirmation timeout logs a warning and still returns the id. `print` replaced by logging.
- Final: 39/39 OK; `check` clean; `makemigrations --check` no changes.

## Breaking change for the frontend
`Mendochain-Web` deletes with `GET` + `PUT`. It must switch `deleteWine` and `deleteTransaction` to `axios.delete(`${apiUrl}/api/<resource>/${id}`)`; until then the delete buttons edit wines and get 405 on transactions.

## Next step
Update `Mendochain-Web` delete calls, then phase 4 (blockchain service refactor).
