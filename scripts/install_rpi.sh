#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Jalankan dengan: sudo bash scripts/install_rpi.sh"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_DIR="/opt/oil-spill-monitor"
if [[ "${PROJECT_DIR}" != "${EXPECTED_DIR}" ]]; then
  echo "Project harus berada di ${EXPECTED_DIR} agar path deployment konsisten."
  echo "Clone ulang dengan: sudo git clone <URL_REPO> ${EXPECTED_DIR}"
  exit 1
fi

APP_USER="${SUDO_USER:-$(stat -c '%U' "${PROJECT_DIR}")}"
if [[ "${APP_USER}" == "root" ]]; then
  echo "Jalankan sudo dari akun user biasa, bukan sesi root langsung."
  exit 1
fi
APP_GROUP="$(id -gn "${APP_USER}")"

echo "[1/6] Memasang package sistem"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl ca-certificates ffmpeg sqlite3 \
  python3-full python3-venv python3-dev python3-opencv \
  build-essential pkg-config libglib2.0-0 libgl1 libjpeg-dev libopenblas-dev

echo "[2/6] Menyiapkan akses perangkat"
python3 - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 atau lebih baru diperlukan")
print(f"Python compatibility OK: {sys.version.split()[0]}")
PY
usermod -aG video "${APP_USER}"
install -d -m 0750 -o root -g "${APP_GROUP}" /etc/oil-spill
install -d -m 0775 -o "${APP_USER}" -g "${APP_GROUP}" "${PROJECT_DIR}/data"
install -d -m 0775 -o "${APP_USER}" -g "${APP_GROUP}" \
  "${PROJECT_DIR}/data/evidence" "${PROJECT_DIR}/data/logs"

echo "[3/6] Membuat Python virtual environment"
if [[ ! -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  sudo -u "${APP_USER}" python3 -m venv --system-site-packages "${PROJECT_DIR}/.venv"
fi
sudo -u "${APP_USER}" "${PROJECT_DIR}/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
sudo -u "${APP_USER}" "${PROJECT_DIR}/.venv/bin/python" -m pip install -r "${PROJECT_DIR}/requirements-rpi.txt"

echo "[4/6] Menyiapkan konfigurasi"
if [[ ! -f /etc/oil-spill/oil-spill.env ]]; then
  install -m 0640 -o root -g "${APP_GROUP}" \
    "${PROJECT_DIR}/.env.example" /etc/oil-spill/oil-spill.env
  echo "Dibuat: /etc/oil-spill/oil-spill.env"
fi
if [[ -f /etc/oil-spill/firebase-service-account.json ]]; then
  chown root:"${APP_GROUP}" /etc/oil-spill/firebase-service-account.json
  chmod 0640 /etc/oil-spill/firebase-service-account.json
fi

echo "[5/6] Memasang systemd services"
sed \
  -e "s|__APP_USER__|${APP_USER}|g" \
  -e "s|__APP_GROUP__|${APP_GROUP}|g" \
  -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
  "${PROJECT_DIR}/systemd/oil-spill-monitor.service" \
  > /etc/systemd/system/oil-spill-monitor.service
sed \
  -e "s|__APP_USER__|${APP_USER}|g" \
  -e "s|__APP_GROUP__|${APP_GROUP}|g" \
  -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
  "${PROJECT_DIR}/systemd/mediamtx.service" \
  > /etc/systemd/system/mediamtx.service
install -m 0644 "${PROJECT_DIR}/systemd/oil-spill-funnel.service" \
  /etc/systemd/system/oil-spill-funnel.service
chmod +x "${PROJECT_DIR}/scripts/"*.sh
systemctl daemon-reload

echo "[6/6] Pemeriksaan awal"
if [[ ! -f "${PROJECT_DIR}/models/best_model.onnx" ]]; then
  echo "ERROR: models/best_model.onnx tidak ditemukan"
  exit 1
fi

echo
echo "Instalasi dasar selesai. Service belum dijalankan."
echo "1. Edit: sudo nano /etc/oil-spill/oil-spill.env"
echo "2. Copy Firebase JSON ke /etc/oil-spill/firebase-service-account.json"
echo "3. Validasi: sudo -u ${APP_USER} ENV_FILE=/etc/oil-spill/oil-spill.env ${PROJECT_DIR}/.venv/bin/python -m app.cli validate"
echo "4. Aktifkan: sudo systemctl enable --now oil-spill-monitor"
