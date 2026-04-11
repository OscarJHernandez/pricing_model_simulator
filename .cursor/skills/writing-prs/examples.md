# PR examples (anonymized)

## Example 1 — Feature

**Title:** `frontend: add experiment inference panel to run detail`

**Body:**

## Summary

Adds a read-only panel on the simulation run detail page that surfaces experiment arm rollups and a link to the batch inference API. Improves discoverability of post-run analysis without changing backend behavior.

## Scope

**In:** New React panel, types aligned with `GET /api/runs/{id}/experiment-inference`, empty and error states.  
**Out:** New endpoints, changes to simulation engine or DB schema.

## How to test

1. Run API and frontend locally; open a run that has experiment-phase data.
2. Confirm the panel shows arm counts and lifts when the endpoint returns 200.
3. Open a run with no experiment data; confirm the empty state copy and no console errors.
4. Stop the API and reload; confirm the error state surfaces gracefully.

## Risks & rollback

Low risk: UI-only. Roll back by reverting the frontend commit; no migration or data cleanup.

## Screenshots / metrics

N/A (add before/after screenshots when UI is finalized).

---

## Example 2 — Bugfix

**Title:** `api: normalize DATABASE_URL scheme for Alembic and app`

**Body:**

## Summary

Ensures `postgresql://` URLs from the host environment are normalized to `postgresql+psycopg://` in both the app session factory and Alembic env so migrations and the API agree on the driver. Fixes connection failures when only the bare `postgresql` scheme is set.

## Scope

**In:** URL normalization in shared DB config used by app and Alembic.  
**Out:** Changing default ports, credentials, or pool settings.

## How to test

1. Set `DATABASE_URL=postgresql://user:pass@localhost:5433/db` (no `+psycopg`).
2. Run `alembic current` and confirm it connects without `psycopg` import errors.
3. Start the API and hit a health or DB-backed route; confirm no startup failure.

## Risks & rollback

Low risk: additive normalization only. Roll back by reverting the config change; no data migration.

## Screenshots / metrics

N/A.
