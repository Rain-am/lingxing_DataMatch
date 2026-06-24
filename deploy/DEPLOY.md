# Deploy Lingxing Data Match On Linux

This guide deploys the app as an isolated systemd service. It does not modify existing projects, existing Nginx config, or public firewall ports.

## 1. Preflight Checks

Run these on the server before deploying:

```bash
ss -lntp | grep 18080 || true
systemctl list-units --type=service | grep lingxing || true
ls /opt
```

Continue only if port `18080` and service name `lingxing-reconcile` are not already used.

## 2. Install System Packages

Ubuntu/Debian:

```bash
apt update
apt install -y git python3 python3-venv python3-pip nodejs npm
```

CentOS/RHEL:

```bash
yum install -y git python3 python3-pip nodejs npm
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

## 5. Install Dependencies And Build Frontend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..
```

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
curl http://127.0.0.1:18080/api/health
```

From your local computer:

```bash
ssh -L 18080:127.0.0.1:18080 root@YOUR_SERVER_IP
```

Open `http://127.0.0.1:18080/`.

## 8. Update Deployment

```bash
cd /opt/lingxing-reconcile
git pull origin main
. .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
cd ..
systemctl restart lingxing-reconcile
```

## Isolation Guarantees

- App directory: `/opt/lingxing-reconcile`
- Service name: `lingxing-reconcile.service`
- Listen address: `127.0.0.1:18080`
- No Nginx changes required
- No public firewall port required
- Secrets remain in `/opt/lingxing-reconcile/backend/.env`
