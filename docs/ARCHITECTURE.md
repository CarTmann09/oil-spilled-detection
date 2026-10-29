# Arsitektur sistem

```text
Hikvision RTSP
    ├── CameraManager → ROI → ONNX/Hailo → mask/area/confidence
    │                                      ↓
    │                              EventEngine 3 dari 5
    │                                      ↓
    │                      SQLite → sync queue → Firebase/Telegram
    │
    └── MediaMTX HLS → Tailscale Funnel → dashboard web
```

## Prinsip ketahanan

- Deteksi tidak bergantung pada Firebase, Telegram, dashboard, MediaMTX, atau Tailscale.
- Semua event disimpan lokal sebelum dikirim keluar.
- Event Firebase menggunakan `eventId` sebagai key agar retry tidak membuat duplikat.
- Heartbeat menggunakan satu queue key dan selalu diganti dengan status terbaru.
- Kamera mencoba tersambung kembali otomatis.
- `systemd` menghidupkan ulang aplikasi jika proses berhenti.
- MediaMTX dan Funnel berjalan sebagai service terpisah dari inference.

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
