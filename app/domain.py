from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np


class DetectionStatus(StrEnum):
    STARTING = "STARTING"
    NORMAL = "NORMAL"
    SUSPECTED = "SUSPECTED"
    SPILL_DETECTED = "TUMPAHAN_TERDETEKSI"
    ERROR = "ERROR"


class Transition(StrEnum):
    NONE = "NONE"
    ALERT_OPENED = "ALERT_OPENED"
    ALERT_CLOSED = "ALERT_CLOSED"


@dataclass(slots=True)
class InferenceResult:
    mask: np.ndarray
    area_ratio: float
    max_probability: float
    mean_mask_probability: float
    inference_ms: float

    @property
    def confidence(self) -> float:
        return self.mean_mask_probability or self.max_probability


@dataclass(slots=True)
class EventDecision:
    status: DetectionStatus
    transition: Transition
    raw_positive: bool
    positive_count: int
    window_size: int
    incident_id: str | None
    occurred_at: datetime
