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

if [[ "${MEDIA_SOURCE_MODE:-remote}" != "file" ]]; then
  echo "File publisher dilewati karena MEDIA_SOURCE_MODE bukan file"
  exit 0
fi
if [[ -z "${MEDIA_FILE_PATH:-}" || ! -f "${MEDIA_FILE_PATH}" ]]; then
  echo "File video tidak ditemukan: ${MEDIA_FILE_PATH:-kosong}"
  exit 1
fi

LOOP_ARGS=()
if [[ "${MEDIA_FILE_LOOP:-true}" == "true" ]]; then
  LOOP_ARGS=(-stream_loop -1)
fi

echo "Publishing local file to MediaMTX path jetty01"
exec ffmpeg \
  -hide_banner -loglevel warning \
  -re "${LOOP_ARGS[@]}" \
  -i "${MEDIA_FILE_PATH}" \
  -map 0:v:0 -an -c:v copy \
  -f rtsp -rtsp_transport tcp \
  rtsp://127.0.0.1:8554/jetty01
