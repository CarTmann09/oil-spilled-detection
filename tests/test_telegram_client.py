from pathlib import Path
from types import SimpleNamespace

from app.telegram_client import TelegramClient


def _settings(**overrides):
    values = {
        "telegram_enabled": True,
        "telegram_send_snapshot": True,
        "telegram_send_recovery": True,
        "telegram_bot_token": "test-token",
        "telegram_chat_id": "-100123",
        "dashboard_url": "",
        "site_name": "Jetty 01",
        "camera_name": "CAM-01",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_alert_uses_album_when_raw_and_overlay_exist(tmp_path, monkeypatch) -> None:
    raw = tmp_path / "raw.jpg"
    overlay = tmp_path / "overlay.jpg"
    raw.write_bytes(b"raw")
    overlay.write_bytes(b"overlay")
    client = TelegramClient(_settings())
    captured = {}

    def fake_media_group(raw_path: Path, overlay_path: Path, caption: str) -> None:
        captured.update(raw=raw_path, overlay=overlay_path, caption=caption)

    monkeypatch.setattr(client, "_post_media_group", fake_media_group)
    client.send_alert(
        {
            "rawSnapshotPath": str(raw),
            "overlaySnapshotPath": str(overlay),
            "snapshotPath": str(overlay),
            "confidence": 0.91,
            "predictedAreaRatio": 0.02,
            "displayTime": "30 October 2026, 22:10:00",
            "incidentId": "OS-301026-001",
        }
    )

    assert captured["raw"] == raw
    assert captured["overlay"] == overlay
    assert "Foto 1: Frame asli tanpa mask" in captured["caption"]
    assert "Foto 2: Hasil segmentasi AI" in captured["caption"]


def test_alert_falls_back_to_single_snapshot(tmp_path, monkeypatch) -> None:
    overlay = tmp_path / "overlay.jpg"
    overlay.write_bytes(b"overlay")
    client = TelegramClient(_settings())
    captured = {}

    def fake_photo(path: Path, caption: str) -> None:
        captured.update(path=path, caption=caption)

    monkeypatch.setattr(client, "_post_photo", fake_photo)
    client.send_alert(
        {
            "snapshotPath": str(overlay),
            "confidence": 0.91,
            "predictedAreaRatio": 0.02,
            "displayTime": "30 October 2026, 22:10:00",
            "incidentId": "OS-301026-001",
        }
    )

    assert captured["path"] == overlay
    assert "Foto 1:" not in captured["caption"]
