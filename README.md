# Lingxing Data Match

Local and server-deployable reconciliation tool for comparing Lingxing data warehouse MySQL aggregates with Lingxing ERP OpenAPI data.

## What It Does

- Stores reconciliation rules in local SQLite.
- Queries Lingxing data warehouse MySQL, optionally through an SSH tunnel.
- Calls Lingxing ERP OpenAPI with `access_token`, `app_key`, `timestamp`, and `sign`.
- Aggregates by day or month and store.
- Shows warehouse value, ERP value, difference, difference rate, and status.
- Exports reconciliation results to Excel.

## Project Layout

- `backend/`: FastAPI backend, SQLite storage, MySQL query, Lingxing API adapter, Excel export.
- `frontend/`: Vue UI.
- `deploy/`: Linux deployment templates for systemd.
- `scripts/`: Windows local helper scripts.

## Local Run On Windows

1. Copy `backend/.env.example` to `backend/.env`.
2. Fill database, SSH tunnel, and Lingxing API credentials in `backend/.env`.
3. Double-click `启动领星对数工具.bat`.
4. Open `http://127.0.0.1:8000/`.

Keep the command window open while using the app.

## Linux Server Deployment

See `deploy/DEPLOY.md`.

Recommended service port:

```text
127.0.0.1:18080
```

Recommended access method:

```bash
ssh -L 18080:127.0.0.1:18080 root@YOUR_SERVER_IP
```

Then open `http://127.0.0.1:18080/`.

## Security Notes

- Never commit `backend/.env`.
- Keep real MySQL, SSH, and Lingxing API credentials only on the machine running the app.
- Add the server public IP to the Lingxing OpenAPI IP allowlist.
- The first server deployment should listen on `127.0.0.1` only and be accessed through SSH port forwarding.
