#!/usr/bin/env bash
set -euo pipefail

sudo systemctl disable --now oil-spill-funnel.service 2>/dev/null || true
sudo tailscale funnel reset
echo "Akses publik Tailscale Funnel sudah dihentikan."
