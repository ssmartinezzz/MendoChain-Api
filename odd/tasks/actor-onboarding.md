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
- [x] R4 API: admin-only user creation; `is_staff` in current user; `GET/POST /api/admin/members`; `DELETE /api/actors/<id>` revokes.
- [x] R5 Web: admin panel (members, onboarding form, revoke) visible to admins only.
- [x] R6 End-to-end on LocalNet.

## Progress
- R1: RED 7, GREEN 24/24; recompiled. `transfer` now asserts a registered sender (`unknown sender`).
- R2: RED 2 (LocalNet), GREEN; admin-signed `revoke_actor` in the adapter. 105/105.
- R3: RED 9 (stubs), GREEN 114/114. `revoked_at` (migration 0008); `onboard_member` creates user + actor atomically; `revoke_actor` revokes on chain before marking; `_actor_of` reads the actor fresh from the database so a cached relation cannot hide a revocation.
- R4: RED 15, GREEN 129/129. `POST /auth/users` admin-only; `is_staff` exposed read-only (a privilege-escalation guard test passes before and after, as the field was absent); `/api/admin/members` (list + onboarding with Django password validators); `DELETE /api/actors/<id>` revokes; revoked recipients rejected by input validation.
- R5 (Mendochain-Web, branch feat/admin-panel): RED 10 + 1 (admin link), GREEN 51/51; build compiles.
- R6 end-to-end on LocalNet (app 1200): bootstrap admin via shell; in the browser the admin onboarded a winery and a distributor from the panel; the winery sent 20 bottles; the admin revoked the distributor (confirmation dialog). On chain: role 0, balance 20 kept. API: the revoked distributor gets 403 `actor_revoked` and is no longer a recipient.
- Known limitation found in R6: actors are bound to one contract deployment but the database does not record which. After a redeploy, old actors show as active while the new app rejects them; documented in the README (re-onboard after redeploy).

## Next step
Open chained PRs (feat/traceability-contract, then feat/actor-onboarding / feat/admin-panel).
