#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Jalankan dengan: sudo bash scripts/install_mediamtx.sh"
  exit 1
fi

ARCH="$(uname -m)"
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
  echo "Arsitektur ${ARCH} bukan ARM64 Raspberry Pi."
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Mencari MediaMTX ARM64 release terbaru..."
curl -fsSL https://api.github.com/repos/bluenviron/mediamtx/releases/latest \
  -o "${TMP_DIR}/release.json"
ASSET_URL="$(python3 - "${TMP_DIR}/release.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    release = json.load(handle)
for asset in release.get("assets", []):
    name = asset.get("name", "")
    if name.endswith("_linux_arm64.tar.gz"):
        print(asset["browser_download_url"])
        break
else:
    raise SystemExit("Asset linux_arm64 tidak ditemukan")
PY
)"

curl -fL "${ASSET_URL}" -o "${TMP_DIR}/mediamtx.tar.gz"
tar -xzf "${TMP_DIR}/mediamtx.tar.gz" -C "${TMP_DIR}"
install -m 0755 "${TMP_DIR}/mediamtx" /usr/local/bin/mediamtx
/usr/local/bin/mediamtx --version

echo "MediaMTX terpasang. Jalankan setelah RTSP_URL di .env valid:"
echo "sudo systemctl enable --now mediamtx"
