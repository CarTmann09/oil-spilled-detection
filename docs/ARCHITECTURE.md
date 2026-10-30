# Arsitektur sistem

```text
Sumber display (HLS/RTSP/file) → MediaMTX path jetty01
                                      ├── HLS → Tailscale Funnel → dashboard
                                      └── RTSP relay ───────────┐
                                                                ↓
Sumber AI: relay MediaMTX atau file lokal → CameraManager → ONNX/Hailo
                                                                ↓
                                                     EventEngine 3 dari 5
                                                                ↓
                                       SQLite → Firebase dan Telegram
```

## Prinsip ketahanan

- Deteksi tidak bergantung pada Firebase, Telegram, dashboard, MediaMTX, atau Tailscale.
- Semua event disimpan lokal sebelum dikirim keluar.
- Event Firebase menggunakan `eventId` sebagai key agar retry tidak membuat duplikat.
- Heartbeat menggunakan satu queue key dan selalu diganti dengan status terbaru.
- Kamera mencoba tersambung kembali otomatis.
- `systemd` menghidupkan ulang aplikasi jika proses berhenti.
- MediaMTX dan Funnel berjalan sebagai service terpisah dari inference.
- Dashboard selalu membaca path `jetty01`. AI dapat membaca path yang sama atau
  file lokal langsung, sehingga pengujian deteksi tidak mengubah tampilan CCTV.

## Mode sumber independen

```bash
# Dashboard Jogja, AI juga membaca Jogja
sudo bash scripts/switch_media_source.sh public
sudo bash scripts/switch_ai_source.sh relay

# Dashboard Jogja, AI membaca video tumpahan lokal
sudo bash scripts/switch_media_source.sh public
sudo bash scripts/switch_ai_source.sh file \
  '/opt/oil-spill-monitor/data/tumpahan-2.mp4'

# Dashboard dan AI sama-sama memakai video lokal
sudo bash scripts/switch_source.sh file \
  '/opt/oil-spill-monitor/data/tumpahan-2.mp4'

# Produksi: dashboard dan AI sama-sama memakai Hikvision
sudo bash scripts/switch_source.sh remote \
  'rtsp://user:password@192.168.1.64:554/Streaming/Channels/102'
```

Mode `remote` membuat MediaMTX menarik HLS/RTSP secara langsung. Mode `file`
mengubah path yang sama menjadi `publisher`, lalu service `oil-spill-source`
memutar file melalui FFmpeg. `switch_ai_source.sh file` tidak mengubah MediaMTX;
model membaca file dan loop langsung melalui `CameraManager`. Firebase dan Telegram
tetap memakai pipeline event yang sama pada semua kombinasi.

## State deteksi

```text
STARTING → NORMAL → SUSPECTED → TUMPAHAN_TERDETEKSI → NORMAL
```

- `SUSPECTED`: satu frame melewati area threshold tetapi belum memenuhi 3 dari 5.
- `TUMPAHAN_TERDETEKSI`: sedikitnya 3 hasil positif dalam 5 pemeriksaan.
- Insiden ditutup setelah 5 pemeriksaan negatif berturut-turut.

## Backend inference

`INFERENCE_BACKEND=onnx` digunakan sekarang. Implementasi Hailo sengaja menolak berjalan
sampai file HEF tersedia dan lolos perbandingan output terhadap ONNX. Komponen lain tidak
perlu diubah ketika backend Hailo ditambahkan.
