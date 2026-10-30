#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"
APP_USER="$(stat -c '%U' "${PROJECT_DIR}")"
APP_GROUP="$(id -gn "${APP_USER}")"

git pull --ff-only
"${PROJECT_DIR}/.venv/bin/python" -m pip install -r requirements-rpi.txt
ENV_FILE=/etc/oil-spill/oil-spill.env "${PROJECT_DIR}/.venv/bin/python" -m app.cli validate
set -a
# shellcheck disable=SC1091
source /etc/oil-spill/oil-spill.env
set +a

for unit in oil-spill-monitor.service mediamtx.service oil-spill-source.service; do
  sed \
    -e "s|__APP_USER__|${APP_USER}|g" \
    -e "s|__APP_GROUP__|${APP_GROUP}|g" \
    -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    "${PROJECT_DIR}/systemd/${unit}" \
    | sudo tee "/etc/systemd/system/${unit}" >/dev/null
done
sudo install -m 0644 "${PROJECT_DIR}/systemd/oil-spill-funnel.service" \
  /etc/systemd/system/oil-spill-funnel.service
sudo chmod +x "${PROJECT_DIR}/scripts/"*.sh
sudo systemctl daemon-reload

sudo systemctl restart mediamtx
if [[ "${MEDIA_SOURCE_MODE:-remote}" == "file" ]]; then
  sudo systemctl enable --now oil-spill-source
  sudo systemctl restart oil-spill-source
else
  sudo systemctl disable --now oil-spill-source >/dev/null 2>&1 || true
fi
sudo systemctl restart oil-spill-monitor
sudo systemctl --no-pager --full status oil-spill-monitor
