# Deploy Lingxing Data Match On Linux

This guide deploys the app as an isolated systemd service. It does not modify existing projects, existing Nginx config, or public firewall ports.

## 1. Preflight Checks

Run these on the server before deploying:

```bash
ss -lntp | grep 18081 || true
systemctl list-units --type=service | grep lingxing || true
ls /opt
```

Continue only if port `18081` and service name `lingxing-reconcile` are not already used.

## 2. Install System Packages

Ubuntu/Debian:

```bash
apt update
apt install -y git python3 python3-venv python3-pip
```

CentOS/RHEL:

```bash
yum install -y git python3 python3-pip
```

## 3. Clone Repository

```bash
git clone git@github.com:Rain-am/lingxing_DataMatch.git /opt/lingxing-reconcile
cd /opt/lingxing-reconcile
```

If using HTTPS instead of a deploy key:

```bash
git clone https://github.com/Rain-am/lingxing_DataMatch.git /opt/lingxing-reconcile
```

## 4. Configure Secrets

Create the server-only config:

```bash
cp backend/.env.example backend/.env
chmod 600 backend/.env
vi backend/.env
```

Fill the real MySQL, SSH tunnel, and Lingxing API values. Do not commit this file.

## 5. Install Dependencies

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
```

The frontend production files are committed under `frontend/dist`, so the server does not need Node.js.

## 6. Install systemd Service

```bash
cp deploy/lingxing-reconcile.service /etc/systemd/system/lingxing-reconcile.service
systemctl daemon-reload
systemctl enable lingxing-reconcile
systemctl start lingxing-reconcile
```

## 7. Verify

```bash
systemctl status lingxing-reconcile
curl http://127.0.0.1:18081/api/health
```

From your local computer:

```bash
ssh -L 18081:127.0.0.1:18081 root@YOUR_SERVER_IP
```

Open `http://127.0.0.1:18081/`.

## 8. Update Deployment

```bash
cd /opt/lingxing-reconcile
git pull origin main
. .venv/bin/activate
pip install -r backend/requirements.txt
systemctl restart lingxing-reconcile
```

## Isolation Guarantees

- App directory: `/opt/lingxing-reconcile`
- Service name: `lingxing-reconcile.service`
- Listen address: `127.0.0.1:18081`
- No Nginx changes required
- No public firewall port required
- Secrets remain in `/opt/lingxing-reconcile/backend/.env`
