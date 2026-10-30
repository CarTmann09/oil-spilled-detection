from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _text(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool = False) -> bool:
    value = _text(name, "true" if default else "false").lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} harus berupa true/false, diterima: {value!r}")


def _int(name: str, default: int) -> int:
    return int(_text(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(_text(name, str(default)))


def _path(name: str, default: str) -> Path:
    return Path(_text(name, default)).expanduser()


def _origins(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _roi(value: str) -> tuple[tuple[float, float], ...]:
    if not value.strip():
        return ()
    points: list[tuple[float, float]] = []
    for raw_point in value.split(";"):
        x_raw, y_raw = raw_point.split(",", maxsplit=1)
        x, y = float(x_raw), float(y_raw)
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("ROI_POLYGON harus memakai koordinat 0 sampai 1")
        points.append((x, y))
    if len(points) < 3:
        raise ValueError("ROI_POLYGON minimal memiliki 3 titik")
    return tuple(points)


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    app_name: str
    site_id: str
    site_name: str
    camera_id: str
    camera_name: str
    timezone: str

    video_source_type: str
    rtsp_url: str
    rtsp_transport: str
    video_file_path: Path
    video_loop: bool
    camera_reconnect_seconds: float
    camera_stale_seconds: float

    roi_polygon: tuple[tuple[float, float], ...]
    inference_backend: str
    onnx_model_path: Path
    hef_model_path: Path
    model_input_width: int
    model_input_height: int
    pixel_threshold: float
    area_threshold: float
    inference_interval_seconds: float
    temporal_window_size: int
    positive_required: int
    negative_to_clear: int
    onnx_intra_op_threads: int
    onnx_inter_op_threads: int

    evidence_directory: Path
    save_raw_snapshot: bool
    save_overlay_snapshot: bool
    evidence_retention_days: int

    sqlite_path: Path
    sync_retry_seconds: int
    sync_max_retry_delay_seconds: int

    firebase_enabled: bool
    firebase_database_url: str
    google_application_credentials: Path
    firebase_live_path: str
    firebase_event_log_path: str
    firebase_incident_path: str
    heartbeat_interval_seconds: int
    daily_summary_enabled: bool
    daily_summary_time: str

    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_send_snapshot: bool
    telegram_send_recovery: bool
    telegram_send_daily_normal: bool
    dashboard_url: str
    hls_public_url: str

    api_host: str
    api_port: int
    api_key: str
    cors_origins: tuple[str, ...]

    log_level: str
    log_directory: Path
    log_retention_days: int
    debug_save_mask: bool

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> Settings:
        candidate = Path(env_file or os.getenv("ENV_FILE", ".env"))
        if candidate.exists():
            load_dotenv(candidate, override=False)

        settings = cls(
            app_env=_text("APP_ENV", "development"),
            app_name=_text("APP_NAME", "oil-spill-monitor"),
            site_id=_text("SITE_ID", "jetty-01"),
            site_name=_text("SITE_NAME", "Jetty 01"),
            camera_id=_text("CAMERA_ID", "cam-01"),
            camera_name=_text("CAMERA_NAME", "CAM-01"),
            timezone=_text("TIMEZONE", "Asia/Singapore"),
            video_source_type=_text("VIDEO_SOURCE_TYPE", "file").lower(),
            rtsp_url=_text("RTSP_URL"),
            rtsp_transport=_text("RTSP_TRANSPORT", "tcp").lower(),
            video_file_path=_path("VIDEO_FILE_PATH", "data/test-video.mp4"),
            video_loop=_bool("VIDEO_LOOP", True),
            camera_reconnect_seconds=_float("CAMERA_RECONNECT_SECONDS", 5),
            camera_stale_seconds=_float("CAMERA_STALE_SECONDS", 15),
            roi_polygon=_roi(_text("ROI_POLYGON")),
            inference_backend=_text("INFERENCE_BACKEND", "onnx").lower(),
            onnx_model_path=_path("ONNX_MODEL_PATH", "models/best_model.onnx"),
            hef_model_path=_path("HEF_MODEL_PATH", "models/best_model.hef"),
            model_input_width=_int("MODEL_INPUT_WIDTH", 1024),
            model_input_height=_int("MODEL_INPUT_HEIGHT", 576),
            pixel_threshold=_float("PIXEL_THRESHOLD", 0.55),
            area_threshold=_float("AREA_THRESHOLD", 0.0055),
            inference_interval_seconds=_float("INFERENCE_INTERVAL_SECONDS", 1),
            temporal_window_size=_int("TEMPORAL_WINDOW_SIZE", 5),
            positive_required=_int("POSITIVE_REQUIRED", 3),
            negative_to_clear=_int("NEGATIVE_TO_CLEAR", 5),
            onnx_intra_op_threads=_int("ONNX_INTRA_OP_THREADS", 4),
            onnx_inter_op_threads=_int("ONNX_INTER_OP_THREADS", 1),
            evidence_directory=_path("EVIDENCE_DIRECTORY", "data/evidence"),
            save_raw_snapshot=_bool("SAVE_RAW_SNAPSHOT", True),
            save_overlay_snapshot=_bool("SAVE_OVERLAY_SNAPSHOT", True),
            evidence_retention_days=_int("EVIDENCE_RETENTION_DAYS", 30),
            sqlite_path=_path("SQLITE_PATH", "data/oil_spill.db"),
            sync_retry_seconds=_int("SYNC_RETRY_SECONDS", 30),
            sync_max_retry_delay_seconds=_int("SYNC_MAX_RETRY_DELAY_SECONDS", 600),
            firebase_enabled=_bool("FIREBASE_ENABLED", False),
            firebase_database_url=_text("FIREBASE_DATABASE_URL"),
            google_application_credentials=_path(
                "GOOGLE_APPLICATION_CREDENTIALS", "secrets/firebase-service-account.json"
            ),
            firebase_live_path=_text("FIREBASE_LIVE_PATH", "/live/jetty-01/cam-01"),
            firebase_event_log_path=_text("FIREBASE_EVENT_LOG_PATH", "/eventLogs"),
            firebase_incident_path=_text("FIREBASE_INCIDENT_PATH", "/incidents"),
            heartbeat_interval_seconds=_int("HEARTBEAT_INTERVAL_SECONDS", 60),
            daily_summary_enabled=_bool("DAILY_SUMMARY_ENABLED", True),
            daily_summary_time=_text("DAILY_SUMMARY_TIME", "23:50"),
            telegram_enabled=_bool("TELEGRAM_ENABLED", False),
            telegram_bot_token=_text("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_text("TELEGRAM_CHAT_ID"),
            telegram_send_snapshot=_bool("TELEGRAM_SEND_SNAPSHOT", True),
            telegram_send_recovery=_bool("TELEGRAM_SEND_RECOVERY", True),
            telegram_send_daily_normal=_bool("TELEGRAM_SEND_DAILY_NORMAL", True),
            dashboard_url=_text("DASHBOARD_URL"),
            hls_public_url=_text("HLS_PUBLIC_URL"),
            api_host=_text("API_HOST", "0.0.0.0"),
            api_port=_int("API_PORT", 8000),
            api_key=_text("API_KEY"),
            cors_origins=_origins(_text("CORS_ORIGINS")),
            log_level=_text("LOG_LEVEL", "INFO").upper(),
            log_directory=_path("LOG_DIRECTORY", "data/logs"),
            log_retention_days=_int("LOG_RETENTION_DAYS", 14),
            debug_save_mask=_bool("DEBUG_SAVE_MASK", False),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.video_source_type not in {"rtsp", "file"}:
            raise ValueError("VIDEO_SOURCE_TYPE harus rtsp atau file")
        if self.video_source_type == "rtsp" and not self.rtsp_url:
            raise ValueError("RTSP_URL wajib diisi ketika VIDEO_SOURCE_TYPE=rtsp")
        if self.inference_backend not in {"onnx", "hailo"}:
            raise ValueError("INFERENCE_BACKEND harus onnx atau hailo")
        if not (0 < self.pixel_threshold < 1):
            raise ValueError("PIXEL_THRESHOLD harus berada antara 0 dan 1")
        if not (0 <= self.area_threshold <= 1):
            raise ValueError("AREA_THRESHOLD harus berada antara 0 dan 1")
        if not (1 <= self.positive_required <= self.temporal_window_size):
            raise ValueError("POSITIVE_REQUIRED harus 1..TEMPORAL_WINDOW_SIZE")
        if self.negative_to_clear < 1:
            raise ValueError("NEGATIVE_TO_CLEAR minimal 1")
        if self.firebase_enabled:
            if not self.firebase_database_url:
                raise ValueError("FIREBASE_DATABASE_URL wajib ketika Firebase aktif")
            if not self.google_application_credentials.exists():
                raise ValueError(
                    "Service account Firebase tidak ditemukan: "
                    f"{self.google_application_credentials}"
                )
        if self.telegram_enabled and (
            not self.telegram_bot_token or not self.telegram_chat_id
        ):
            raise ValueError("TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID wajib diisi")
        hour, minute = self.daily_summary_time.split(":", maxsplit=1)
        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            raise ValueError("DAILY_SUMMARY_TIME harus berformat HH:MM")

    def ensure_directories(self) -> None:
        for directory in (
            self.evidence_directory,
            self.sqlite_path.parent,
            self.log_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)
