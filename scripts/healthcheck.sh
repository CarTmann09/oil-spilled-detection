#!/usr/bin/env bash
set -euo pipefail

echo "=== Oil Spill Service ==="
systemctl --no-pager --full status oil-spill-monitor || true
echo
echo "=== MediaMTX ==="
systemctl --no-pager --full status mediamtx || true
echo
echo "=== Tailscale ==="
tailscale status || true
tailscale funnel status || true
echo
echo "=== Local API ==="
curl -fsS http://127.0.0.1:8000/health
echo
