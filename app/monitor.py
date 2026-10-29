from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .camera import CameraManager
from .config import Settings
from .domain import DetectionStatus, InferenceResult, Transition
from .event_engine import EventEngine
from .evidence import EvidenceManager
from .firebase_client import FirebaseClient
from .health import system_metrics
from .inference.hailo_engine import HailoEngine
from .inference.onnx_engine import OnnxEngine
from .runtime import RuntimeState
from .storage import Storage
from .telegram_client import TelegramClient

LOGGER = logging.getLogger(__name__)


class OilSpillMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.timezone = ZoneInfo(settings.timezone)
        self.state = RuntimeState(settings.site_id, settings.camera_id)
        self.storage = Storage(settings.sqlite_path)
        self.camera = CameraManager(settings)
        self.evidence = EvidenceManager(settings)
        self.firebase = FirebaseClient(settings)
        self.telegram = TelegramClient(settings)
        self.event_engine = EventEngine(
            settings.temporal_window_size,
            settings.positive_required,
            settings.negative_to_clear,
        )
        if settings.inference_backend == "onnx":
            self.engine = OnnxEngine(
                settings.onnx_model_path,
                settings.model_input_width,
                settings.model_input_height,
                settings.pixel_threshold,
                settings.roi_polygon,
                settings.onnx_intra_op_threads,
                settings.onnx_inter_op_threads,
            )
        else:
            self.engine = HailoEngine(settings.hef_model_path)

        self._tasks: list[asyncio.Task[Any]] = []
        self._stopping = asyncio.Event()
        self._last_camera_status = "STARTING"
        self._last_result: InferenceResult | None = None

    async def start(self) -> None:
        self.camera.start()
        self.state.update(
            systemStatus="ONLINE",
            inferenceStatus="RUNNING",
            backend=self.engine.backend_name,
        )
        startup_payload = self._persist_event(
            event_type="SYSTEM_STARTED",
            status="ONLINE",
            message="Oil Spill Monitoring System aktif",
        )
        if self.settings.firebase_enabled:
            self._enqueue(
                "firebase_event", startup_payload["eventId"], startup_payload
            )
        self._tasks = [
            asyncio.create_task(self._detection_loop(), name="detection-loop"),
            asyncio.create_task(self._sync_loop(), name="sync-loop"),
            asyncio.create_task(self._heartbeat_loop(), name="heartbeat-loop"),
            asyncio.create_task(self._daily_summary_loop(), name="daily-summary-loop"),
        ]
        LOGGER.info("Monitoring service started backend=%s", self.engine.backend_name)

    async def stop(self) -> None:
        self._stopping.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self.camera.stop()
        self.storage.close()
        LOGGER.info("Monitoring service stopped")

    async def _detection_loop(self) -> None:
        last_frame_id = -1
        last_inference_at = 0.0
        while not self._stopping.is_set():
            camera_status = self.camera.status
            self.state.update(cameraStatus=camera_status)
            if camera_status != self._last_camera_status:
                self._record_camera_transition(camera_status)
                self._last_camera_status = camera_status

            packet = self.camera.latest()
            now_monotonic = time.monotonic()
            if (
                packet is None
                or packet.frame_id == last_frame_id
                or now_monotonic - last_inference_at
                < self.settings.inference_interval_seconds
            ):
                await asyncio.sleep(0.1)
                continue

            last_frame_id = packet.frame_id
            last_inference_at = now_monotonic
            occurred_at = packet.captured_at.astimezone(self.timezone)
            try:
                result = await asyncio.to_thread(self.engine.infer, packet.frame)
                self._last_result = result
                raw_positive = result.area_ratio >= self.settings.area_threshold
                decision = self.event_engine.update(raw_positive, occurred_at)
                self.state.update(
                    systemStatus="ONLINE",
                    cameraStatus=camera_status,
                    inferenceStatus="RUNNING",
                    detectionStatus=decision.status.value,
                    confidence=round(result.confidence, 6),
                    maxProbability=round(result.max_probability, 6),
                    predictedAreaRatio=round(result.area_ratio, 8),
                    incidentId=self.event_engine.incident_id,
                    lastDetectionAtMs=int(occurred_at.timestamp() * 1000),
                    inferenceMs=round(result.inference_ms, 2),
                    lastError=None,
                )

                if decision.transition == Transition.ALERT_OPENED:
                    await self._open_incident(packet.frame, result, decision)
                elif decision.transition == Transition.ALERT_CLOSED:
                    self._close_incident(result, decision)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # service must survive an inference failure
                LOGGER.exception("Inference failed")
                self.state.update(
                    inferenceStatus="ERROR",
                    detectionStatus=DetectionStatus.ERROR.value,
                    lastError=str(exc),
                )
                await asyncio.sleep(max(1.0, self.settings.inference_interval_seconds))

    async def _open_incident(self, frame, result, decision) -> None:
        incident_id = decision.incident_id
        if incident_id is None:
            return
        evidence = await asyncio.to_thread(
            self.evidence.save,
            frame,
            result,
            incident_id,
            decision.occurred_at,
        )
        snapshot_path = evidence.get("overlay") or evidence.get("raw")
        self.state.update(latestSnapshotPath=snapshot_path)
        payload = self._persist_event(
            event_type="INCIDENT_OPENED",
            status=DetectionStatus.SPILL_DETECTED.value,
            message=f"Indikasi tumpahan terdeteksi di {self.settings.site_name}",
            confidence=result.confidence,
            area_ratio=result.area_ratio,
            incident_id=incident_id,
            snapshot_path=snapshot_path,
            occurred_at=decision.occurred_at,
        )
        incident = {
            **payload,
            "openedAtMs": payload["timestampMs"],
            "incidentStatus": "OPEN",
        }
        self._enqueue_external(payload, telegram_channel="telegram_alert")
        self._enqueue("firebase_incident", incident_id, incident)
        LOGGER.warning("Incident opened id=%s", incident_id)

    def _close_incident(self, result, decision) -> None:
        incident_id = decision.incident_id
        payload = self._persist_event(
            event_type="INCIDENT_CLOSED",
            status=DetectionStatus.NORMAL.value,
            message=f"Kondisi kembali normal di {self.settings.site_name}",
            confidence=result.confidence,
            area_ratio=result.area_ratio,
            incident_id=incident_id,
            occurred_at=decision.occurred_at,
        )
        self._enqueue_external(payload, telegram_channel="telegram_recovery")
        if incident_id:
            incident = {
                **payload,
                "closedAtMs": payload["timestampMs"],
                "incidentStatus": "CLOSED",
            }
            self._enqueue("firebase_incident", incident_id, incident)
        LOGGER.info("Incident closed id=%s", incident_id)

    def _record_camera_transition(self, status: str) -> None:
        payload = self._persist_event(
            event_type="CAMERA_STATUS_CHANGED",
            status=status,
            message=f"Status kamera berubah menjadi {status}",
        )
        if self.settings.firebase_enabled:
            self._enqueue("firebase_event", payload["eventId"], payload)

    async def _heartbeat_loop(self) -> None:
        while not self._stopping.is_set():
            now = datetime.now(UTC)
            metrics = await asyncio.to_thread(system_metrics, self.settings.sqlite_path.parent)
            self.state.update(
                lastHeartbeatAtMs=int(now.timestamp() * 1000),
                systemMetrics=metrics,
                syncQueueSize=self.storage.queue_size(),
            )
            if self.settings.firebase_enabled:
                self._enqueue(
                    "firebase_live", "live_status", self.public_status(include_metrics=True)
                )
            await asyncio.sleep(self.settings.heartbeat_interval_seconds)

    async def _sync_loop(self) -> None:
        while not self._stopping.is_set():
            now_ms = int(datetime.now(UTC).timestamp() * 1000)
            items = self.storage.due_items(now_ms)
            for item in items:
                try:
                    await asyncio.to_thread(self._dispatch, item)
                    self.storage.mark_done(int(item["id"]))
                except Exception as exc:
                    attempts = int(item["attempts"]) + 1
                    self.storage.mark_failed(
                        int(item["id"]),
                        attempts,
                        str(exc),
                        now_ms,
                        self.settings.sync_retry_seconds,
                        self.settings.sync_max_retry_delay_seconds,
                    )
                    LOGGER.warning(
                        "Sync failed channel=%s attempt=%s error=%s",
                        item["channel"],
                        attempts,
                        exc,
                    )
            await asyncio.sleep(1)

    def _dispatch(self, item: dict[str, Any]) -> None:
        channel = item["channel"]
        payload = item["payload"]
        if channel == "firebase_live":
            self.firebase.set_live(payload)
        elif channel == "firebase_event":
            self.firebase.set_event(payload)
        elif channel == "firebase_incident":
            self.firebase.set_incident(payload)
        elif channel == "telegram_alert":
            self.telegram.send_alert(payload)
        elif channel == "telegram_recovery":
            self.telegram.send_recovery(payload)
        else:
            raise ValueError(f"Channel sync tidak dikenal: {channel}")

    async def _daily_summary_loop(self) -> None:
        target_hour, target_minute = map(int, self.settings.daily_summary_time.split(":"))
        while not self._stopping.is_set():
            now = datetime.now(self.timezone)
            key = f"daily_summary:{now.date().isoformat()}"
            if (
                self.settings.daily_summary_enabled
                and (now.hour, now.minute) >= (target_hour, target_minute)
                and self.storage.get_metadata(key) is None
            ):
                state = self.state.snapshot()
                payload = self._persist_event(
                    event_type="DAILY_SUMMARY",
                    status=str(state["detectionStatus"]),
                    message=f"Ringkasan monitoring harian {self.settings.site_name}",
                    confidence=float(state.get("confidence") or 0),
                    area_ratio=float(state.get("predictedAreaRatio") or 0),
                    incident_id=state.get("incidentId"),
                    occurred_at=now,
                )
                if self.settings.firebase_enabled:
                    self._enqueue("firebase_event", payload["eventId"], payload)
                self.storage.set_metadata(key, "sent")
                removed = await asyncio.to_thread(self.evidence.cleanup, now)
                LOGGER.info("Daily summary created, evidence removed=%s", removed)
            await asyncio.sleep(20)

    def _persist_event(
        self,
        event_type: str,
        status: str,
        message: str,
        confidence: float = 0.0,
        area_ratio: float = 0.0,
        incident_id: str | None = None,
        snapshot_path: str | None = None,
        occurred_at: datetime | None = None,
    ) -> dict[str, Any]:
        local_time = (occurred_at or datetime.now(self.timezone)).astimezone(self.timezone)
        payload: dict[str, Any] = {
            "eventId": str(uuid.uuid4()),
            "timestampMs": int(local_time.timestamp() * 1000),
            "displayTime": local_time.strftime("%d %B %Y, %H:%M:%S"),
            "siteId": self.settings.site_id,
            "cameraId": self.settings.camera_id,
            "type": event_type,
            "status": status,
            "confidence": round(float(confidence), 6),
            "predictedAreaRatio": round(float(area_ratio), 8),
            "incidentId": incident_id,
            "message": message,
            "snapshotPath": snapshot_path,
        }
        self.storage.record_event(payload)
        return payload

    def _enqueue_external(
        self, payload: dict[str, Any], telegram_channel: str | None = None
    ) -> None:
        if self.settings.firebase_enabled:
            self._enqueue("firebase_event", payload["eventId"], payload)
        if self.settings.telegram_enabled and telegram_channel:
            self._enqueue(telegram_channel, payload["eventId"], payload)

    def _enqueue(
        self, channel: str, unique_key: str, payload: dict[str, Any]
    ) -> None:
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        self.storage.enqueue(channel, str(unique_key), payload, now_ms)

    def public_status(self, include_metrics: bool = True) -> dict[str, Any]:
        state = self.state.snapshot()
        public = {
            "siteId": state["siteId"],
            "cameraId": state["cameraId"],
            "systemStatus": state["systemStatus"],
            "cameraStatus": state["cameraStatus"],
            "inferenceStatus": state["inferenceStatus"],
            "detectionStatus": state["detectionStatus"],
            "confidence": state["confidence"],
            "predictedAreaRatio": state["predictedAreaRatio"],
            "incidentId": state["incidentId"],
            "lastDetectionAtMs": state["lastDetectionAtMs"],
            "lastHeartbeatAtMs": state["lastHeartbeatAtMs"],
            "inferenceMs": state["inferenceMs"],
            "backend": state["backend"],
            "streamUrl": self.settings.hls_public_url or None,
        }
        if include_metrics:
            public["systemMetrics"] = state.get("systemMetrics")
        return public
