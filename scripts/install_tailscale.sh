#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Jalankan dengan: sudo bash scripts/install_tailscale.sh"
  exit 1
fi

TMP_SCRIPT="$(mktemp)"
trap 'rm -f "${TMP_SCRIPT}"' EXIT
curl -fsSL https://tailscale.com/install.sh -o "${TMP_SCRIPT}"
sh "${TMP_SCRIPT}"
systemctl enable --now tailscaled

echo "Tailscale terpasang. Login dengan:"
echo "sudo tailscale up --hostname=jetty01-pi"
