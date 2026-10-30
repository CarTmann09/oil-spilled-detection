#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Shortcut: mengatur MediaMTX dan AI memakai source yang sama.

Penggunaan:
  sudo bash scripts/switch_source.sh public
  sudo bash scripts/switch_source.sh remote <URL_HLS_ATAU_RTSP>
  sudo bash scripts/switch_source.sh file <PATH_VIDEO_LOKAL>

Contoh:
  sudo bash scripts/switch_source.sh public
  sudo bash scripts/switch_source.sh remote 'rtsp://user:pass@192.168.1.64:554/Streaming/Channels/102'
  sudo bash scripts/switch_source.sh file '/opt/oil-spill-monitor/data/tumpahan-2.mp4'
EOF
}

ACTION="${1:-}"
VALUE="${2:-}"
case "${ACTION}" in
  public)
    SKIP_MONITOR_RESTART=true bash "${PROJECT_DIR}/scripts/switch_media_source.sh" public
    ;;
  remote)
    [[ -n "${VALUE}" ]] || { usage; exit 1; }
    SKIP_MONITOR_RESTART=true bash "${PROJECT_DIR}/scripts/switch_media_source.sh" remote "${VALUE}"
    ;;
  file)
    [[ -n "${VALUE}" ]] || { usage; exit 1; }
    SKIP_MONITOR_RESTART=true bash "${PROJECT_DIR}/scripts/switch_media_source.sh" file "${VALUE}"
    ;;
  *)
    usage
    exit 1
    ;;
esac
bash "${PROJECT_DIR}/scripts/switch_ai_source.sh" relay
echo "MediaMTX dan AI sekarang memakai source yang sama."
