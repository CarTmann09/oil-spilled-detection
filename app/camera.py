from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import cv2
import numpy as np

from .config import Settings

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class FramePacket:
    frame_id: int
    captured_at: datetime
    frame: np.ndarray


class CameraManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._packet: FramePacket | None = None
        self._frame_id = 0
        self._status = "STARTING"
        self._last_error = ""
        self._last_frame_monotonic = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, name="camera-reader", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def latest(self) -> FramePacket | None:
        with self._lock:
            if self._packet is None:
                return None
            return FramePacket(
                frame_id=self._packet.frame_id,
                captured_at=self._packet.captured_at,
                frame=self._packet.frame.copy(),
            )

    @property
    def status(self) -> str:
        if (
            self._last_frame_monotonic
            and time.monotonic() - self._last_frame_monotonic
            > self.settings.camera_stale_seconds
        ):
            return "OFFLINE"
        with self._lock:
            return self._status

    @property
    def last_error(self) -> str:
        with self._lock:
            return self._last_error

    def _set_status(self, status: str, error: str = "") -> None:
        with self._lock:
            changed = status != self._status or error != self._last_error
            self._status = status
            self._last_error = error
        if changed:
            if error:
                LOGGER.warning("Camera status=%s error=%s", status, error)
            else:
                LOGGER.info("Camera status=%s", status)

    def _open(self) -> cv2.VideoCapture:
        if self.settings.video_source_type == "rtsp":
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;{self.settings.rtsp_transport}|stimeout;10000000"
            )
            source = self.settings.rtsp_url
        else:
            source = str(self.settings.video_file_path)
        capture = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return capture

    def _run(self) -> None:
        while not self._stop.is_set():
            capture = self._open()
            if not capture.isOpened():
                self._set_status("RECONNECTING", "Sumber video gagal dibuka")
                self._stop.wait(self.settings.camera_reconnect_seconds)
                continue

            source_fps = capture.get(cv2.CAP_PROP_FPS)
            frame_period = 1.0 / source_fps if source_fps and source_fps > 0 else 0.04
            self._set_status("CONNECTED")

            while not self._stop.is_set():
                started = time.monotonic()
                ok, frame = capture.read()
                if not ok:
                    if (
                        self.settings.video_source_type == "file"
                        and self.settings.video_loop
                    ):
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    self._set_status("RECONNECTING", "Frame tidak tersedia")
                    break

                self._frame_id += 1
                packet = FramePacket(self._frame_id, datetime.now(UTC), frame)
                with self._lock:
                    self._packet = packet
                    self._status = "CONNECTED"
                    self._last_error = ""
                    self._last_frame_monotonic = time.monotonic()

                if self.settings.video_source_type == "file":
                    elapsed = time.monotonic() - started
                    self._stop.wait(max(0.0, frame_period - elapsed))

            capture.release()
            if not self._stop.is_set():
                self._stop.wait(self.settings.camera_reconnect_seconds)
