#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

git pull --ff-only
"${PROJECT_DIR}/.venv/bin/python" -m pip install -r requirements-rpi.txt
ENV_FILE=/etc/oil-spill/oil-spill.env "${PROJECT_DIR}/.venv/bin/python" -m app.cli validate
sudo systemctl restart oil-spill-monitor
if systemctl list-unit-files mediamtx.service >/dev/null 2>&1; then
  sudo systemctl restart mediamtx || true
fi
sudo systemctl --no-pager --full status oil-spill-monitor
