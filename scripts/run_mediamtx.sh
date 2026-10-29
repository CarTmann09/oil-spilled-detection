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

if [[ -z "${RTSP_URL:-}" || "${RTSP_URL}" == *"USERNAME:PASSWORD"* ]]; then
  echo "RTSP_URL belum diisi dengan benar"
  exit 1
fi

export MTX_PATHS_JETTY01_SOURCE="${RTSP_URL}"
exec /usr/local/bin/mediamtx "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/config/mediamtx.yml"
