#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-/etc/oil-spill/oil-spill.env}"
PUBLIC_HLS_URL="https://cctvjss.jogjakota.go.id/malioboro/Malioboro_3_Depan_Dispar.stream/playlist.m3u8"

usage() {
  cat <<'EOF'
Mengatur stream yang ditampilkan MediaMTX/dashboard:
  sudo bash scripts/switch_media_source.sh public
  sudo bash scripts/switch_media_source.sh remote <URL_HLS_ATAU_RTSP>
  sudo bash scripts/switch_media_source.sh file <PATH_VIDEO_LOKAL>
EOF
}

[[ ${EUID} -eq 0 ]] || { echo "Jalankan dengan sudo"; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "Environment file tidak ditemukan: ${ENV_FILE}"; exit 1; }

ACTION="${1:-}"
VALUE="${2:-}"
case "${ACTION}" in
  public)
    MODE="remote"
    SOURCE_URL="${PUBLIC_HLS_URL}"
    FILE_PATH=""
    ;;
  remote)
    [[ -n "${VALUE}" ]] || { usage; exit 1; }
    MODE="remote"
    SOURCE_URL="${VALUE}"
    FILE_PATH=""
    ;;
  file)
    [[ -n "${VALUE}" ]] || { usage; exit 1; }
    [[ "${VALUE}" == /* ]] || { echo "Path video harus absolut"; exit 1; }
    [[ -f "${VALUE}" ]] || { echo "File video tidak ditemukan: ${VALUE}"; exit 1; }
    MODE="file"
    SOURCE_URL=""
    FILE_PATH="${VALUE}"
    ;;
  *)
    usage
    exit 1
    ;;
esac

python3 "${PROJECT_DIR}/scripts/update_env.py" "${ENV_FILE}" \
  "MEDIA_SOURCE_MODE=${MODE}" \
  "MEDIA_SOURCE_URL=${SOURCE_URL}" \
  "MEDIA_FILE_PATH=${FILE_PATH}"

systemctl enable --now mediamtx.service
systemctl restart mediamtx.service
if [[ "${MODE}" == "file" ]]; then
  systemctl enable --now oil-spill-source.service
  systemctl restart oil-spill-source.service
else
  systemctl disable --now oil-spill-source.service >/dev/null 2>&1 || true
fi

if [[ "${SKIP_MONITOR_RESTART:-false}" != "true" ]]; then
  systemctl try-restart oil-spill-monitor.service
fi

echo
echo "Media/dashboard source aktif: mode=${MODE}"
echo "HLS lokal: http://127.0.0.1:8888/jetty01/"
