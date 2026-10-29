#!/usr/bin/env bash
set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  echo "Tailscale belum terpasang. Jalankan scripts/install_tailscale.sh"
  exit 1
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "Tailscale belum login. Jalankan: sudo tailscale up --hostname=jetty01-pi"
  exit 1
fi
if ! systemctl is-active --quiet mediamtx; then
  echo "MediaMTX belum aktif. Jalankan: sudo systemctl enable --now mediamtx"
  exit 1
fi

sudo tailscale funnel --bg 8888
sudo systemctl enable oil-spill-funnel.service

echo
echo "Funnel aktif. URL stream adalah URL HTTPS berikut ditambah /jetty01/:"
tailscale funnel status
