# Open Issues

This is the active project issue register for agents. Keep it factual and update
it when work starts or finishes. Do not use chat history as the only record of an
open item.

## High Priority

### OI-001 - Keep committed frontend dist aligned with frontend source

- Status: open
- Area: frontend/deployment
- Context: FastAPI serves `frontend/dist` in local `.bat` and Linux deployment.
  When `frontend/src` changes, the committed `dist` bundle can become stale.
- Impact: Users running without Node/build may see old UI behavior.
- Next action: Whenever frontend source changes, run the allowed frontend build
  and commit the updated `frontend/dist` assets, or document a deliberate reason
  for not shipping dist.
- Progress: 2026-06-26 run reconciliation UI changes rebuilt `frontend/dist`
  with `npm.cmd run build` after `pnpm` was unavailable.

### OI-002 - Clarify Windows launch paths and dependency assumptions

- Status: open
- Area: operations
- Context: The root `.bat` starts only the backend and uses committed dist.
  `scripts/start-app.ps1` rebuilds the frontend and depends on local runtime
  paths plus frontend dependencies.
- Impact: Operators may not know which launcher to use or why behavior differs.
- Next action: Decide whether both launch paths should remain. If yes, document
  the intended audience for each and the prerequisites.

### OI-003 - Decide persistence model for background batch jobs

- Status: open
- Area: backend API
- Context: Batch job state is stored in process memory. Finished reconcile runs
  are persisted, but job progress/status disappears on backend restart.
- Impact: Long-running jobs cannot be recovered or inspected after restart.
- Next action: Decide whether in-memory job status is acceptable for local use,
  or design a SQLite-backed job table.

## Medium Priority

### OI-004 - Document real Lingxing field mapping examples

- Status: open
- Area: data sources
- Context: The code supports nested fields such as `data>>sids`, request-month
  mode, and fixed USD currency, but the repository lacks domain examples for
  common Lingxing modules.
- Impact: Rule creation requires tribal knowledge.
- Next action: Add sanitized examples to a new docs file or module doc after
  confirming field names against real API responses.

### OI-005 - Add user-facing error and empty-state review

- Status: open
- Area: frontend
- Context: API errors are surfaced directly to the UI. This is useful during
  development, but production users may need clearer next steps.
- Impact: Failed credentials, bad fields, or API shape changes may be hard for
  non-developers to resolve.
- Next action: Review common failures and map them to actionable messages.

### OI-006 - Expand README into operator and developer paths

- Status: open
- Area: documentation
- Context: README is concise and now points to deeper docs, but it still mixes
  product description, Windows run, Linux deploy, and security notes.
- Impact: New users can start, but developers and operators need more precise
  guidance.
- Next action: Split detailed guidance into docs while keeping README short.

## Low Priority

### OI-007 - Consider frontend component split

- Status: open
- Area: frontend
- Context: Most UI behavior currently lives in `frontend/src/App.vue`.
- Impact: The single file is workable now but will grow harder to maintain as
  new views and rule helpers are added.
- Next action: Split only when a frontend feature change creates real pressure;
  avoid a cosmetic refactor by itself.

### OI-008 - Add module docs examples for test commands

- Status: open
- Area: tests
- Context: Backend tests are present, but no standard local command matrix is
  documented beyond the module testing page.
- Impact: Agents may run too broad or too little verification.
- Next action: Add targeted command examples as testing needs become stable.
