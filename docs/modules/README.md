# Module Index

Use these module files as the project map. Update the owning module file whenever
behavior changes.

## Modules

- `backend-api.md`: FastAPI routes, batch jobs, response contracts.
- `reconciliation-core.md`: aggregation, comparison, statuses, summaries.
- `data-sources.md`: MySQL warehouse adapter, SSH tunnel, Lingxing OpenAPI,
  token/signing/pagination, store mapping.
- `storage-schema.md`: SQLite tables, schema models, compatibility fields.
- `frontend-ui.md`: Vue screens, API calls, user workflow, dist behavior.
- `export-reporting.md`: Excel export behavior.
- `deployment-operations.md`: Windows and Linux operations, scripts, ports,
  secrets.
- `testing.md`: backend test map and verification expectations.

## Current Directory Shape

```text
backend/
  app/
    config.py
    exporter.py
    lianxing_api.py
    main.py
    reconcile.py
    schemas.py
    storage.py
    validation.py
    warehouse.py
  tests/
frontend/
  src/
  dist/
deploy/
scripts/
docs/
```

## Ownership Rules

- API contract change: update `backend-api.md`, `storage-schema.md` if models
  change, and frontend docs if consumed by UI.
- Reconciliation math change: update `reconciliation-core.md`, tests, and export
  docs if output columns change.
- Data-fetch behavior change: update `data-sources.md` and any sanitized field
  examples.
- UI workflow change: update `frontend-ui.md`; rebuild `frontend/dist` if the
  change should ship through committed assets.
- Deployment/script change: update `deployment-operations.md` and README if a
  user-facing command changes.

