#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-/etc/oil-spill/oil-spill.env}"
PYTHON="${PROJECT_DIR}/.venv/bin/python"

fail() {
  echo "PREFLIGHT ERROR: $*" >&2
  exit 1
}

[[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "arm64" ]] \
  || fail "Raspberry Pi OS harus 64-bit ARM"
[[ -x "${PYTHON}" ]] || fail "Virtual environment belum tersedia"
"${PYTHON}" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 atau lebih baru diperlukan")
PY
[[ -f "${ENV_FILE}" ]] || fail "Environment file tidak ditemukan: ${ENV_FILE}"
[[ -f "${PROJECT_DIR}/models/best_model.onnx" ]] || fail "Model ONNX tidak ditemukan"
command -v ffmpeg >/dev/null || fail "ffmpeg belum terpasang"

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ "${VIDEO_SOURCE_TYPE:-}" == "rtsp" ]]; then
  [[ -n "${RTSP_URL:-}" && "${RTSP_URL}" != *"USERNAME:PASSWORD"* ]] \
    || fail "RTSP_URL belum diisi"
fi
if [[ "${FIREBASE_ENABLED:-false}" == "true" ]]; then
  [[ -n "${FIREBASE_DATABASE_URL:-}" ]] || fail "FIREBASE_DATABASE_URL kosong"
  [[ -f "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]] \
    || fail "Firebase service account JSON tidak ditemukan"
fi
if [[ "${TELEGRAM_ENABLED:-false}" == "true" ]]; then
  [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] || fail "TELEGRAM_BOT_TOKEN kosong"
  [[ -n "${TELEGRAM_CHAT_ID:-}" ]] || fail "TELEGRAM_CHAT_ID kosong"
fi

FREE_KB="$(df -Pk "${PROJECT_DIR}" | awk 'NR==2 {print $4}')"
(( FREE_KB >= 2 * 1024 * 1024 )) || fail "Sisa storage kurang dari 2 GB"

ENV_FILE="${ENV_FILE}" "${PYTHON}" -m app.cli validate
ENV_FILE="${ENV_FILE}" "${PYTHON}" -m app.cli check-model

if [[ "${1:-}" == "--with-camera" ]]; then
  ENV_FILE="${ENV_FILE}" "${PYTHON}" -m app.cli check-camera --timeout 20
fi

echo "PREFLIGHT_OK"
