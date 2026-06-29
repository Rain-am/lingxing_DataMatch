# Deployment And Operations Module

Owner files:

- `README.md`
- `backend/.env.example`
- `deploy/DEPLOY.md`
- `deploy/lingxing-reconcile.service`
- `scripts/launch-app.ps1`
- `scripts/start-app.ps1`
- `scripts/stop-app.ps1`
- `启动领星对数工具.bat`

## Windows Local Run

Primary simple path:

1. Copy `backend/.env.example` to `backend/.env`.
2. Fill MySQL, optional SSH tunnel, and Lingxing API credentials.
3. Double-click `启动领星对数工具.bat`.
4. Open `http://127.0.0.1:8000/`.

The root `.bat` starts the backend and relies on committed `frontend/dist`.

PowerShell helper path:

- `scripts/launch-app.ps1` launches `scripts/start-app.ps1` hidden, waits, and
  checks `/api/health`.
- `scripts/start-app.ps1` rebuilds the frontend and then starts uvicorn on
  `127.0.0.1:8000`.
- `scripts/stop-app.ps1` stops processes listening on port `8000`.

## Linux Server Deployment

Recommended isolated deployment:

- App directory: `/opt/lingxing-reconcile`
- Service name: `lingxing-reconcile.service`
- Listen address: `127.0.0.1:18081`
- Access through SSH port forwarding
- No public firewall port and no Nginx changes required for the initial setup

See `deploy/DEPLOY.md`.

## Secrets

Never commit:

- `backend/.env`
- MySQL passwords
- SSH passwords or keys
- Lingxing access tokens, refresh tokens, app secrets
- Real API response samples with sensitive business data

## Change Checklist

- Update README when a user-facing run command changes.
- Update `deploy/DEPLOY.md` for Linux operational changes.
- Update `.env.example` when adding settings.
- Do not stop or restart services unless the user asks for operational action.

