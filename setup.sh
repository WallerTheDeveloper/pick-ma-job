#!/usr/bin/env bash
# setup.sh — First-time server setup for pick-ma-job on Ubuntu 24.04.
#
# Usage:
#   scp setup.sh root@<droplet-ip>:/root/setup.sh
#   ssh root@<droplet-ip> 'bash /root/setup.sh'
#
# After running this script:
#   1. Edit /opt/pick-ma-job/.env with production values
#   2. Run: certbot --nginx -d pickmajob.cc
#   3. Run: systemctl start pick-ma-job.service

set -euo pipefail

DOMAIN="pickmajob.cc"
APP_DIR="/opt/pick-ma-job"

echo "==> Updating system packages..."
apt update && apt upgrade -y

echo "==> Installing dependencies..."
apt install -y \
  nginx \
  python3.12 \
  python3.12-venv \
  nodejs \
  npm \
  certbot \
  python3-certbot-nginx \
  git \
  postgresql \
  postgresql-client

# ── PostgreSQL setup ─────────────────────────────────────────────────────
echo "==> Setting up PostgreSQL..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='pickmajob'" | grep -q 1 || \
  sudo -u postgres createuser pickmajob
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='pickmajob'" | grep -q 1 || \
  sudo -u postgres createdb -O pickmajob pickmajob

# Set a random password for the DB user
DB_PASS=$(openssl rand -hex 16)
sudo -u postgres psql -c "ALTER USER pickmajob WITH PASSWORD '${DB_PASS}';"
echo "  Database password: ${DB_PASS}"
echo "  DATABASE_URL=postgresql://pickmajob:${DB_PASS}@localhost:5432/pickmajob"

# ── Clone repo ───────────────────────────────────────────────────────────
if [ ! -d "$APP_DIR" ]; then
  echo "==> Cloning repository..."
  echo "  Place your repo at ${APP_DIR} (git clone or scp)"
  echo "  Then re-run this script."
  mkdir -p "$APP_DIR"
fi

if [ ! -f "$APP_DIR/main.py" ]; then
  echo "ERROR: ${APP_DIR}/main.py not found. Clone the repo first."
  exit 1
fi

cd "$APP_DIR"

# ── Python venv ──────────────────────────────────────────────────────────
echo "==> Creating Python venv..."
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# ── Frontend build ───────────────────────────────────────────────────────
echo "==> Building frontend..."
cd frontend
npm ci
npm run build
cd "$APP_DIR"

# ── .env file ────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "==> Creating .env from template..."
  cat > .env <<EOF
# pick-ma-job production environment
BASE_URL=https://${DOMAIN}

# PostgreSQL
DATABASE_URL=postgresql://pickmajob:${DB_PASS}@localhost:5432/pickmajob

# Claude API
ANTHROPIC_API_KEY=

# Apify
APIFY_API_TOKEN=

# Auth / Email
MAGIC_LINK_SECRET=$(openssl rand -hex 32)
RESEND_API_KEY=
EMAIL_FROM=
ADMIN_EMAIL=

# FastAPI
SECRET_KEY=$(openssl rand -hex 32)
EOF
  echo "  Created .env — fill in the blank values!"
fi

# ── Systemd service ──────────────────────────────────────────────────────
echo "==> Installing systemd service..."
cp systemd/job-pipeline.service /etc/systemd/system/pick-ma-job.service
systemctl daemon-reload
systemctl enable pick-ma-job.service

# ── Nginx ────────────────────────────────────────────────────────────────
echo "==> Configuring nginx..."
cp nginx/pick-ma-job.conf /etc/nginx/sites-available/pick-ma-job.conf
ln -sf /etc/nginx/sites-available/pick-ma-job.conf /etc/nginx/sites-enabled/pick-ma-job.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── Permissions ──────────────────────────────────────────────────────────
echo "==> Setting permissions..."
chown -R www-data:www-data "$APP_DIR"

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit /opt/pick-ma-job/.env (fill in API keys)"
echo "  2. Start the service:  systemctl start pick-ma-job.service"
echo "  3. Install SSL:        certbot --nginx -d ${DOMAIN}"
echo "  4. Verify:             curl https://${DOMAIN}/health"
echo ""
