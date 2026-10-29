from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from .config import Settings
from .domain import InferenceResult


class EvidenceManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save(
        self,
        frame: np.ndarray,
        result: InferenceResult,
        incident_id: str,
        occurred_at: datetime,
    ) -> dict[str, str | None]:
        directory = self.settings.evidence_directory / occurred_at.strftime("%Y-%m-%d")
        directory.mkdir(parents=True, exist_ok=True)
        raw_path: Path | None = None
        overlay_path: Path | None = None

        if self.settings.save_raw_snapshot:
            raw_path = directory / f"{incident_id}-raw.jpg"
            if not cv2.imwrite(str(raw_path), frame):
                raise RuntimeError(f"Gagal menyimpan snapshot: {raw_path}")

        if self.settings.save_overlay_snapshot:
            overlay = self._overlay(frame, result, incident_id, occurred_at)
            overlay_path = directory / f"{incident_id}-overlay.jpg"
            if not cv2.imwrite(str(overlay_path), overlay):
                raise RuntimeError(f"Gagal menyimpan overlay: {overlay_path}")

        if self.settings.debug_save_mask:
            full_mask = cv2.resize(
                result.mask.astype(np.uint8) * 255,
                (frame.shape[1], frame.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )
            cv2.imwrite(str(directory / f"{incident_id}-mask.png"), full_mask)

        return {
            "raw": str(raw_path) if raw_path else None,
            "overlay": str(overlay_path) if overlay_path else None,
        }

    def cleanup(self, now: datetime) -> int:
        removed = 0
        cutoff = now.timestamp() - self.settings.evidence_retention_days * 86400
        root = self.settings.evidence_directory
        if not root.exists():
            return removed
        for path in root.rglob("*"):
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        for directory in sorted(root.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        return removed

    def _overlay(
        self,
        frame: np.ndarray,
        result: InferenceResult,
        incident_id: str,
        occurred_at: datetime,
    ) -> np.ndarray:
        output = frame.copy()
        full_mask = cv2.resize(
            result.mask.astype(np.uint8),
            (frame.shape[1], frame.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool)
        if full_mask.any():
            red = np.zeros_like(output)
            red[:, :, 2] = 255
            blended = cv2.addWeighted(output, 0.58, red, 0.42, 0)
            output[full_mask] = blended[full_mask]
            contours, _ = cv2.findContours(
                full_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(output, contours, -1, (0, 220, 255), 2)

        panel_width = min(output.shape[1] - 20, 780)
        cv2.rectangle(output, (12, 12), (panel_width, 152), (12, 22, 32), -1)
        lines = (
            "TUMPAHAN MINYAK TERDETEKSI",
            f"{self.settings.site_name} / {self.settings.camera_name}",
            f"Waktu: {occurred_at:%Y-%m-%d %H:%M:%S}",
            f"Area: {result.area_ratio * 100:.3f}%  Confidence: {result.confidence * 100:.1f}%",
            f"ID: {incident_id}",
        )
        for index, line in enumerate(lines):
            color = (30, 60, 255) if index == 0 else (245, 245, 245)
            scale = 0.72 if index == 0 else 0.56
            cv2.putText(
                output,
                line,
                (28, 42 + index * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                color,
                2,
                cv2.LINE_AA,
            )
        return output
