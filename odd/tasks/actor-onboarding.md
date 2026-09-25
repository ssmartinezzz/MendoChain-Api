# Actor onboarding and revocation

## Objective
Let the admin onboard supply-chain participants from a panel and revoke their role on chain.

## Decisions
- User (2026-09-25): option A, onboarding by the admin (no public signup); the contract gets role revocation.
- Onboarding is one use case: user + custodial account + on-chain role in a single database transaction; a ledger failure leaves no user behind.
- Only admins create user accounts (`POST /auth/users` was open to any signed-in user).
- Revoked actors are frozen on chain: they cannot register lots, send or receive bottles. Balances stay on chain as evidence. Reactivation is out of scope.
- The contract changes, so it is redeployed (it only ran on LocalNet so far).
- Chained on top of `feat/traceability-contract`.

## TDD
- Mode: strict (source: global user configuration)
- Contract: `uv run --group contracts pytest contracts`
- API: `DB_NAME=mendochain DB_USER=test DB_PASSWORD=test DB_HOST=localhost DB_PORT=55432 SECRET_KEY=test LOG_LEVEL=WARNING uv run python manage.py test`
- Web: `CI=true npm test -- --watchAll=false`

## Tasks
- [x] R1 Contract: `revoke_actor` (admin only, registered accounts); revoked or unregistered accounts cannot send.
- [x] R2 Ledger port, fake and Algorand adapter: `revoke_actor`; LocalNet test.
- [x] R3 Domain: `Actor.revoked_at`; `onboard_member` and `revoke_actor` services; revoked actors excluded from recipients and rejected early.
- [ ] R4 API: admin-only user creation; `is_staff` in current user; `GET/POST /api/admin/members`; `DELETE /api/actors/<id>` revokes.
- [ ] R5 Web: admin panel (members, onboarding form, revoke) visible to admins only.
- [ ] R6 End-to-end on LocalNet.

## Progress
- R1: RED 7, GREEN 24/24; recompiled. `transfer` now asserts a registered sender (`unknown sender`).
- R2: RED 2 (LocalNet), GREEN; admin-signed `revoke_actor` in the adapter. 105/105.
- R3: RED 9 (stubs), GREEN 114/114. `revoked_at` (migration 0008); `onboard_member` creates user + actor atomically; `revoke_actor` revokes on chain before marking; `_actor_of` reads the actor fresh from the database so a cached relation cannot hide a revocation.

## Next step
R4.
