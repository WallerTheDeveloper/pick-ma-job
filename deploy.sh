#!/usr/bin/env bash
# deploy.sh — Pull latest code, build frontend, restart services.
#
# Usage:
#   ssh server 'cd /opt/pick-ma-job && bash deploy.sh'
#
# Prerequisites:
#   - Node.js 20+ and npm installed on the server
#   - Python venv at /opt/pick-ma-job/.venv
#   - systemd unit: pick-ma-job.service
#   - nginx config symlinked: /etc/nginx/sites-enabled/pick-ma-job.conf

set -euo pipefail

APP_DIR="/opt/pick-ma-job"
cd "$APP_DIR"

echo "==> Pulling latest code..."
git pull --ff-only

echo "==> Installing Python dependencies..."
.venv/bin/pip install -r requirements.txt --quiet

echo "==> Building frontend..."
cd frontend
npm ci --silent
npm run build
cd "$APP_DIR"

echo "==> Restarting backend..."
sudo systemctl restart pick-ma-job.service

echo "==> Reloading nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo "==> Deploy complete."
