from __future__ import annotations

import threading
from copy import deepcopy
from datetime import UTC, datetime


class RuntimeState:
    def __init__(self, site_id: str, camera_id: str) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, object] = {
            "siteId": site_id,
            "cameraId": camera_id,
            "systemStatus": "STARTING",
            "cameraStatus": "STARTING",
            "inferenceStatus": "STARTING",
            "detectionStatus": "STARTING",
            "confidence": 0.0,
            "maxProbability": 0.0,
            "predictedAreaRatio": 0.0,
            "incidentId": None,
            "lastDetectionAtMs": None,
            "lastHeartbeatAtMs": None,
            "inferenceMs": None,
            "backend": None,
            "lastError": None,
            "latestSnapshotPath": None,
            "startedAtMs": int(datetime.now(UTC).timestamp() * 1000),
        }

    def update(self, **values: object) -> None:
        with self._lock:
            self._data.update(values)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return deepcopy(self._data)
