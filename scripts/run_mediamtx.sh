#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/oil-spill/oil-spill.env}"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file tidak ditemukan: ${ENV_FILE}"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

MODE="${MEDIA_SOURCE_MODE:-remote}"
case "${MODE}" in
  remote)
    # Backward compatible: env lama masih dapat memakai RTSP_URL langsung,
    # selama nilainya bukan relay MediaMTX itu sendiri.
    SOURCE_URL="${MEDIA_SOURCE_URL:-${RTSP_URL:-}}"
    if [[ -z "${SOURCE_URL}" || "${SOURCE_URL}" == *"USERNAME:PASSWORD"* ]]; then
      echo "MEDIA_SOURCE_URL belum diisi dengan benar"
      exit 1
    fi
    if [[ "${SOURCE_URL}" == "rtsp://127.0.0.1:8554/jetty01" ]]; then
      echo "MEDIA_SOURCE_URL tidak boleh menunjuk kembali ke relay lokal"
      exit 1
    fi
    export MTX_PATHS_JETTY01_SOURCE="${SOURCE_URL}"
    ;;
  file)
    [[ -n "${MEDIA_FILE_PATH:-}" ]] || {
      echo "MEDIA_FILE_PATH wajib diisi untuk mode file"
      exit 1
    }
    export MTX_PATHS_JETTY01_SOURCE="publisher"
    ;;
  *)
    echo "MEDIA_SOURCE_MODE harus remote atau file"
    exit 1
    ;;
esac

echo "MediaMTX source mode=${MODE} path=jetty01"
exec /usr/local/bin/mediamtx "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/config/mediamtx.yml"
