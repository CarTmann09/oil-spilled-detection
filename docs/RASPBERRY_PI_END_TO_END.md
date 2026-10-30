# Instalasi Raspberry Pi end-to-end

Panduan ini untuk branch `test/e2e-onnx-public-hls`, Raspberry Pi 5 64-bit,
inference ONNX CPU, MediaMTX, Telegram, dan Tailscale Funnel. HEF/Hailo belum
digunakan pada branch ini.

## 1. Persiapan Raspberry Pi OS

```bash
sudo apt update
sudo apt full-upgrade -y
sudo timedatectl set-timezone Asia/Singapore
sudo reboot
```

Setelah masuk kembali:

```bash
uname -m
python3 --version
df -h /
```

Target: arsitektur `aarch64`, Python minimal 3.11, dan ruang kosong minimal 2 GB.

Pastikan tanggal Raspberry Pi benar karena ID insiden dan jadwal ringkasan harian
mengikuti waktu perangkat:

```bash
timedatectl status
```

## 2. Clone branch pengujian

```bash
sudo mkdir -p /opt
sudo chown "$USER":"$USER" /opt
git clone --branch test/e2e-onnx-public-hls \
  https://github.com/CarTmann09/oil-spilled-detection.git \
  /opt/oil-spill-monitor
cd /opt/oil-spill-monitor
```

## 3. Install backend dan service dasar

```bash
sudo bash scripts/install_rpi.sh
sudo bash scripts/install_mediamtx.sh
sudo bash scripts/install_tailscale.sh
```

`install_rpi.sh` memasang FFmpeg, SQLite, OpenCV, Python virtual environment,
dependensi aplikasi, serta unit `systemd`. Model ONNX sudah tersedia di folder
`models`, jadi tidak perlu menyalin model secara manual.

## 4. Isi konfigurasi

```bash
sudo nano /etc/oil-spill/oil-spill.env
```

Minimal untuk tes Telegram tanpa Firebase:

```dotenv
INFERENCE_BACKEND=onnx
ONNX_MODEL_PATH=/opt/oil-spill-monitor/models/best_model.onnx

FIREBASE_ENABLED=false

TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=GANTI_TOKEN
TELEGRAM_CHAT_ID=-100XXXXXXXXXX
TELEGRAM_SEND_SNAPSHOT=true
TELEGRAM_SEND_RECOVERY=true
TELEGRAM_SEND_DAILY_NORMAL=true

DASHBOARD_URL=https://monitor-oil-leak.vercel.app/
DAILY_SUMMARY_ENABLED=true
DAILY_SUMMARY_TIME=23:50
```

Amankan file:

```bash
sudo chown root:"$(id -gn)" /etc/oil-spill/oil-spill.env
sudo chmod 640 /etc/oil-spill/oil-spill.env
```

## 5. Copy video tumpahan untuk pengujian

Jalankan dari laptop:

```bash
scp "tumpahan 2.mp4" USER_RASPI@IP_RASPI:/tmp/tumpahan-2.mp4
```

Kemudian di Raspberry Pi:

```bash
sudo mv /tmp/tumpahan-2.mp4 /opt/oil-spill-monitor/data/tumpahan-2.mp4
sudo chown "$USER":"$(id -gn)" /opt/oil-spill-monitor/data/tumpahan-2.mp4
chmod 640 /opt/oil-spill-monitor/data/tumpahan-2.mp4
```

## 6. Login Tailscale

```bash
sudo tailscale up --hostname=jetty01-pi
tailscale status
```

Buka URL login yang ditampilkan jika diminta.

## 7. Pilih kombinasi source

Dashboard Jogja dan AI Jogja:

```bash
cd /opt/oil-spill-monitor
sudo bash scripts/switch_media_source.sh public
sudo bash scripts/switch_ai_source.sh relay
```

Dashboard Jogja dan AI video tumpahan lokal yang loop:

```bash
sudo bash scripts/switch_media_source.sh public
sudo bash scripts/switch_ai_source.sh file \
  /opt/oil-spill-monitor/data/tumpahan-2.mp4
```

Dashboard dan AI sama-sama video lokal:

```bash
sudo bash scripts/switch_source.sh file \
  /opt/oil-spill-monitor/data/tumpahan-2.mp4
```

Produksi Hikvision untuk dashboard dan AI:

```bash
sudo bash scripts/switch_source.sh remote \
  'rtsp://USER:PASSWORD@IP_CCTV:554/Streaming/Channels/102'
```

## 8. Validasi sebelum start

```bash
ENV_FILE=/etc/oil-spill/oil-spill.env \
bash scripts/preflight.sh --with-camera
```

Hasil yang diharapkan:

```text
PREFLIGHT_OK
```

## 9. Jalankan sistem

```bash
sudo systemctl enable --now mediamtx
sudo systemctl enable --now oil-spill-monitor
sudo systemctl status mediamtx --no-pager
sudo systemctl status oil-spill-monitor --no-pager
```

Jika MediaMTX menggunakan video lokal, `switch_media_source.sh file` otomatis
mengaktifkan `oil-spill-source.service`.

## 10. Aktifkan Tailscale Funnel

```bash
cd /opt/oil-spill-monitor
bash scripts/configure_funnel.sh
tailscale funnel status
```

Jika Tailscale meminta persetujuan Funnel, buka URL yang ditampilkan dan aktifkan
Funnel untuk tailnet tersebut, lalu ulangi `bash scripts/configure_funnel.sh`.

Funnel memberikan base URL seperti:

```text
https://jetty01-pi.NAMA-TAILNET.ts.net
```

URL player dashboard:

```text
https://jetty01-pi.NAMA-TAILNET.ts.net/jetty01/
```

URL manifest HLS:

```text
https://jetty01-pi.NAMA-TAILNET.ts.net/jetty01/index.m3u8
```

Masukkan URL player ke environment:

```bash
sudo nano /etc/oil-spill/oil-spill.env
```

```dotenv
HLS_PUBLIC_URL=https://jetty01-pi.NAMA-TAILNET.ts.net/jetty01/
```

Kemudian:

```bash
sudo systemctl restart oil-spill-monitor
```

Dashboard Vercel harus memakai URL `HLS_PUBLIC_URL` tersebut sebagai sumber
player. Jangan memasukkan URL RTSP ke browser; browser membaca HLS HTTPS dari
Funnel.

## 11. Pemeriksaan sistem

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8888/jetty01/index.m3u8
bash scripts/healthcheck.sh
sudo journalctl -u mediamtx -f
sudo journalctl -u oil-spill-source -f
sudo journalctl -u oil-spill-monitor -f
```

Data lokal:

```text
/opt/oil-spill-monitor/data/oil_spill.db
/opt/oil-spill-monitor/data/evidence/
/opt/oil-spill-monitor/data/logs/
```

Query event terakhir:

```bash
sqlite3 /opt/oil-spill-monitor/data/oil_spill.db \
  "SELECT datetime(timestamp_ms/1000,'unixepoch','localtime'),type,status,incident_id FROM events ORDER BY timestamp_ms DESC LIMIT 20;"
```

## 12. Update branch

```bash
cd /opt/oil-spill-monitor
git status
git pull --ff-only origin test/e2e-onnx-public-hls
bash scripts/deploy_update.sh
```

## 13. Stop dan recovery

```bash
sudo systemctl restart oil-spill-monitor
sudo systemctl restart mediamtx
sudo systemctl stop oil-spill-monitor
bash scripts/stop_public_stream.sh
```

Funnel bersifat publik. Matikan setelah pengujian jika tidak diperlukan.
