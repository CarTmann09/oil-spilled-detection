#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-/etc/oil-spill/oil-spill.env}"

usage() {
  cat <<'EOF'
Mengatur video yang dibaca model ONNX:
  sudo bash scripts/switch_ai_source.sh relay
  sudo bash scripts/switch_ai_source.sh file <PATH_VIDEO_LOKAL>

relay = membaca path MediaMTX jetty01 yang sama dengan dashboard.
file  = membaca video lokal langsung dan melakukan loop.
EOF
}

[[ ${EUID} -eq 0 ]] || { echo "Jalankan dengan sudo"; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "Environment file tidak ditemukan: ${ENV_FILE}"; exit 1; }

ACTION="${1:-}"
VALUE="${2:-}"
case "${ACTION}" in
  relay)
    python3 "${PROJECT_DIR}/scripts/update_env.py" "${ENV_FILE}" \
      "VIDEO_SOURCE_TYPE=rtsp" \
      "RTSP_URL=rtsp://127.0.0.1:8554/jetty01"
    systemctl enable --now mediamtx.service
    DESCRIPTION="MediaMTX relay jetty01"
    ;;
  file)
    [[ -n "${VALUE}" ]] || { usage; exit 1; }
    [[ "${VALUE}" == /* ]] || { echo "Path video harus absolut"; exit 1; }
    [[ -f "${VALUE}" ]] || { echo "File video tidak ditemukan: ${VALUE}"; exit 1; }
    python3 "${PROJECT_DIR}/scripts/update_env.py" "${ENV_FILE}" \
      "VIDEO_SOURCE_TYPE=file" \
      "VIDEO_FILE_PATH=${VALUE}" \
      "VIDEO_LOOP=true"
    DESCRIPTION="file lokal ${VALUE} (loop)"
    ;;
  *)
    usage
    exit 1
    ;;
esac

systemctl try-restart oil-spill-monitor.service
echo
echo "AI source aktif: ${DESCRIPTION}"
