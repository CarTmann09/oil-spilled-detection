# Firebase dan dashboard

## Status realtime

Path:

```text
/live/jetty-01/cam-01
```

Field utama:

```json
{
  "systemStatus": "ONLINE",
  "cameraStatus": "CONNECTED",
  "inferenceStatus": "RUNNING",
  "detectionStatus": "NORMAL",
  "confidence": 0.0,
  "predictedAreaRatio": 0.0,
  "incidentId": null,
  "lastDetectionAtMs": 0,
  "lastHeartbeatAtMs": 0,
  "backend": "ONNXRuntime-CPU",
  "streamUrl": "https://node.tailnet.ts.net/jetty01/"
}
```

Dashboard menganggap perangkat offline jika `now - lastHeartbeatAtMs > 120000`.

## Event dan insiden

```text
/eventLogs/{eventId}
/incidents/{incidentId}
```

Dashboard mengambil 10 hari terakhir, mengurutkan `timestampMs`, menampilkan 50 data per
halaman, dan membuat file Excel di sisi browser.

## Live stream

Setelah Funnel aktif, masukkan URL ke `HLS_PUBLIC_URL` dan gunakan iframe:

```html
<iframe
  src="https://node.tailnet.ts.net/jetty01/?autoplay=true&muted=true&controls=true"
  title="Live CCTV Jetty 01"
  allow="autoplay; fullscreen"
></iframe>
```

Rules dalam `firebase/database.rules.poc.json` membuat data monitoring dapat dibaca publik
tetapi hanya Admin SDK Raspberry Pi yang dapat menulis. Rules ini cocok untuk PoC; tambahkan
Firebase Authentication sebelum sistem memuat data sensitif.
