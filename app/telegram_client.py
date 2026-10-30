from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .config import Settings


class TelegramClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.telegram_enabled

    def send_alert(self, payload: dict[str, Any]) -> None:
        raw = self._existing_path(payload.get("rawSnapshotPath"))
        overlay = self._existing_path(payload.get("overlaySnapshotPath"))
        snapshot = self._existing_path(payload.get("snapshotPath"))
        if self.settings.telegram_send_snapshot and raw and overlay:
            caption = self._alert_caption(payload, include_album_legend=True)
            self._post_media_group(raw, overlay, caption)
        elif self.settings.telegram_send_snapshot and snapshot:
            caption = self._alert_caption(payload)
            self._post_photo(snapshot, caption)
        else:
            caption = self._alert_caption(payload)
            self._post_message(caption)

    def send_recovery(self, payload: dict[str, Any]) -> None:
        if not self.settings.telegram_send_recovery:
            return
        message = (
            "🟢 <b>KONDISI KEMBALI NORMAL</b>\n\n"
            f"📍 <b>Lokasi:</b> {html.escape(self.settings.site_name)}\n"
            f"🎥 <b>Kamera:</b> {html.escape(self.settings.camera_name)}\n"
            f"🆔 <b>ID Insiden:</b> {html.escape(str(payload.get('incidentId') or '-'))}\n"
            f"🕒 <b>Waktu:</b> {html.escape(str(payload.get('displayTime') or '-'))}"
        )
        self._post_message(message)

    def _alert_caption(
        self, payload: dict[str, Any], include_album_legend: bool = False
    ) -> str:
        confidence = float(payload.get("confidence", 0)) * 100
        area = float(payload.get("predictedAreaRatio", 0)) * 100
        caption = (
            "🚨 <b>TUMPAHAN MINYAK TERDETEKSI</b>\n\n"
            f"📍 <b>Lokasi:</b> {html.escape(self.settings.site_name)}\n"
            f"🎥 <b>Kamera:</b> {html.escape(self.settings.camera_name)}\n"
            "🔴 <b>Status:</b> Terdeteksi\n"
            f"📊 <b>Confidence:</b> {confidence:.1f}%\n"
            f"📐 <b>Area indikasi:</b> {area:.3f}%\n"
            f"🕒 <b>Waktu:</b> {html.escape(str(payload.get('displayTime') or '-'))}\n"
            f"🆔 <b>ID Insiden:</b> {html.escape(str(payload.get('incidentId') or '-'))}\n\n"
            "⚠️ Mohon segera periksa kondisi di lokasi."
        )
        if include_album_legend:
            caption += (
                "\n\n📷 Foto 1: Frame asli tanpa mask\n"
                "🟥 Foto 2: Hasil segmentasi AI"
            )
        return caption

    @staticmethod
    def _existing_path(value: Any) -> Path | None:
        if not value:
            return None
        path = Path(str(value))
        return path if path.is_file() else None

    def _reply_markup(self) -> str | None:
        if not self.settings.dashboard_url:
            return None
        return json.dumps(
            {
                "inline_keyboard": [
                    [{"text": "CEK DASHBOARD", "url": self.settings.dashboard_url}]
                ]
            }
        )

    def _post_photo(self, path: Path, caption: str) -> None:
        import httpx

        url = (
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendPhoto"
        )
        data = {
            "chat_id": self.settings.telegram_chat_id,
            "caption": caption,
            "parse_mode": "HTML",
        }
        markup = self._reply_markup()
        if markup:
            data["reply_markup"] = markup
        with path.open("rb") as handle:
            response = httpx.post(
                url,
                data=data,
                files={"photo": (path.name, handle, "image/jpeg")},
                timeout=30,
            )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram menolak foto: {result}")

    def _post_media_group(self, raw_path: Path, overlay_path: Path, caption: str) -> None:
        import httpx

        url = (
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}"
            "/sendMediaGroup"
        )
        media = [
            {
                "type": "photo",
                "media": "attach://raw",
                "caption": caption,
                "parse_mode": "HTML",
            },
            {"type": "photo", "media": "attach://overlay"},
        ]
        with raw_path.open("rb") as raw_handle, overlay_path.open("rb") as overlay_handle:
            response = httpx.post(
                url,
                data={
                    "chat_id": self.settings.telegram_chat_id,
                    "media": json.dumps(media, ensure_ascii=False),
                },
                files={
                    "raw": (raw_path.name, raw_handle, "image/jpeg"),
                    "overlay": (overlay_path.name, overlay_handle, "image/jpeg"),
                },
                timeout=30,
            )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram menolak album foto: {result}")
        # Telegram albums do not support inline keyboards. Preserve the dashboard
        # action as a separate compact message only when a URL has been configured.
        if self.settings.dashboard_url:
            self._post_message("🔗 <b>Dashboard monitoring</b>")

    def _post_message(self, message: str) -> None:
        import httpx

        url = (
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        )
        payload: dict[str, Any] = {
            "chat_id": self.settings.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        markup = self._reply_markup()
        if markup:
            payload["reply_markup"] = json.loads(markup)
        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram menolak pesan: {result}")
