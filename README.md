# Oil Spill Monitoring System — Jetty 01

Paket deployment Raspberry Pi 5 untuk mengambil RTSP Hikvision, menjalankan segmentasi
tumpahan minyak, membuat insiden, menyimpan bukti, mengirim Telegram, menyinkronkan Firebase
Realtime Database, serta menyediakan live HLS melalui MediaMTX dan Tailscale Funnel.

## Yang sudah disertakan

- Model ONNX V3 `1024×576`.
- Threshold pixel `0.55`, minimum area `0.0055`.
- Validasi temporal 3 dari 5 dan clear setelah 5 negatif.
- Camera reader dengan latest-frame strategy dan reconnect.
- SQLite WAL dan antrean retry offline.
- Firebase status, event log, incident, dan heartbeat 60 detik.
- Telegram alert dengan album frame asli dan overlay segmentasi AI. Sistem otomatis
  kembali ke satu foto atau pesan teks jika bukti tidak lengkap.
- Tombol dashboard opsional; untuk album, Telegram menampilkannya sebagai pesan
  tombol terpisah karena `sendMediaGroup` tidak mendukung inline keyboard.
- Notifikasi normal harian dikirim satu kali pada waktu yang dikonfigurasi hanya
  jika tidak pernah ada tumpahan pada tanggal tersebut dan sistem sedang normal.
- Insiden aktif dipulihkan dari SQLite setelah restart sehingga tumpahan yang sama
  tidak membuka ID dan notifikasi baru.
- FastAPI health/status/event/snapshot.
- MediaMTX HLS dan Tailscale Funnel.
- Source switcher independen: dashboard tetap melalui path MediaMTX `jetty01`,
  sedangkan AI dapat membaca relay tersebut atau video lokal yang di-loop.
- Service `systemd`, installer, health check, serta unit test.

## Kebutuhan Raspberry Pi

- Raspberry Pi 5, Raspberry Pi OS 64-bit dengan Python 3.11 atau lebih baru.
- Git dan koneksi internet saat instalasi.
- CCTV Hikvision dapat dijangkau melalui LAN.
- Firebase Realtime Database dan service-account JSON.
- Telegram bot token serta chat ID grup.
- Hailo tidak diperlukan pada tahap awal.

## Deployment pertama

Clone tepat ke `/opt/oil-spill-monitor`:

```bash
sudo mkdir -p /opt
sudo chown "$USER":"$USER" /opt
git clone <URL_REPOSITORY> /opt/oil-spill-monitor
cd /opt/oil-spill-monitor
sudo bash scripts/install_rpi.sh
```

Untuk branch pengujian ini, source dashboard dan AI dapat dipilih terpisah:

```bash
# Dashboard Jogja, AI Jogja
sudo bash scripts/switch_media_source.sh public
sudo bash scripts/switch_ai_source.sh relay

# Dashboard Jogja, AI video lokal loop
sudo bash scripts/switch_media_source.sh public
sudo bash scripts/switch_ai_source.sh file \
  /opt/oil-spill-monitor/data/tumpahan-2.mp4

# Dashboard dan AI memakai source yang sama
sudo bash scripts/switch_source.sh remote \
  'rtsp://user:password@192.168.1.64:554/Streaming/Channels/102'
```

Jika Raspberry Pi sebelumnya memakai `main`, pindah ke branch pengujian dan pasang
unit source baru dengan:

```bash
cd /opt/oil-spill-monitor
git fetch origin
git switch --track origin/test/e2e-onnx-public-hls
bash scripts/deploy_update.sh
```

Copy video uji sebelum memilih mode file:

```bash
scp "tumpahan 2.mp4" USER_RASPI@IP_RASPI:/tmp/tumpahan-2.mp4
sudo mv /tmp/tumpahan-2.mp4 /opt/oil-spill-monitor/data/tumpahan-2.mp4
sudo chown "$USER":"$(id -gn)" /opt/oil-spill-monitor/data/tumpahan-2.mp4
sudo bash scripts/switch_source.sh file \
  /opt/oil-spill-monitor/data/tumpahan-2.mp4
```

Edit environment:

```bash
sudo nano /etc/oil-spill/oil-spill.env
```

Yang wajib diisi:

```dotenv
RTSP_URL=rtsp://user:password@alamat-kamera:554/Streaming/Channels/102
FIREBASE_ENABLED=true
FIREBASE_DATABASE_URL=https://project-default-rtdb.asia-southeast1.firebasedatabase.app
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=token-baru
TELEGRAM_CHAT_ID=-100xxxxxxxxxx
DASHBOARD_URL=https://alamat-dashboard
```

Copy Firebase credential tanpa memasukkannya ke Git:

```bash
sudo cp firebase-service-account.json /etc/oil-spill/firebase-service-account.json
sudo chown root:"$(id -gn)" /etc/oil-spill/firebase-service-account.json
sudo chmod 640 /etc/oil-spill/firebase-service-account.json
```

Validasi sebelum menjalankan service:

```bash
cd /opt/oil-spill-monitor
ENV_FILE=/etc/oil-spill/oil-spill.env bash scripts/preflight.sh --with-camera
```

Aktifkan aplikasi:

```bash
sudo systemctl enable --now oil-spill-monitor
sudo journalctl -u oil-spill-monitor -f
```

API lokal:

```bash
curl http://127.0.0.1:8000/health
```

## Live stream publik

Pasang MediaMTX:

```bash
cd /opt/oil-spill-monitor
sudo bash scripts/install_mediamtx.sh
sudo systemctl enable --now mediamtx
```

Pasang dan login Tailscale:

```bash
sudo bash scripts/install_tailscale.sh
sudo tailscale up --hostname=jetty01-pi
bash scripts/configure_funnel.sh
```

Salin URL hasil Funnel, tambahkan `/jetty01/`, lalu isi `HLS_PUBLIC_URL` pada environment.

Untuk menghentikan akses publik:

```bash
bash scripts/stop_public_stream.sh
```

## Update dari Git

```bash
cd /opt/oil-spill-monitor
bash scripts/deploy_update.sh
```

## Diagnosis

```bash
bash scripts/healthcheck.sh
sudo journalctl -u oil-spill-monitor -n 200 --no-pager
sudo journalctl -u mediamtx -n 200 --no-pager
```

## Tes lokal pengembangan

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Gunakan `.env.example` sebagai dasar `.env`. Jangan commit `.env`, token Telegram, password
RTSP, atau service-account Firebase.

Dokumentasi tambahan tersedia di `docs/ARCHITECTURE.md` dan
`docs/FIREBASE_AND_DASHBOARD.md`.
