from __future__ import annotations

from collections import deque
from datetime import datetime

from .domain import DetectionStatus, EventDecision, Transition


class EventEngine:
    def __init__(
        self,
        temporal_window: int,
        positive_required: int,
        negative_to_clear: int,
    ) -> None:
        self._window: deque[int] = deque(maxlen=temporal_window)
        self._positive_required = positive_required
        self._negative_to_clear = negative_to_clear
        self._event_open = False
        self._negative_streak = 0
        self._incident_id: str | None = None

    def update(self, raw_positive: bool, occurred_at: datetime) -> EventDecision:
        self._window.append(1 if raw_positive else 0)
        transition = Transition.NONE
        decision_incident = self._incident_id

        if self._event_open:
            self._negative_streak = 0 if raw_positive else self._negative_streak + 1
            if self._negative_streak >= self._negative_to_clear:
                transition = Transition.ALERT_CLOSED
                decision_incident = self._incident_id
                self._event_open = False
                self._incident_id = None
                self._negative_streak = 0
                self._window.clear()
                status = DetectionStatus.NORMAL
            else:
                status = DetectionStatus.SPILL_DETECTED
        elif (
            len(self._window) == self._window.maxlen
            and sum(self._window) >= self._positive_required
        ):
            self._event_open = True
            self._negative_streak = 0
            self._incident_id = f"OS-{occurred_at:%Y%m%d-%H%M%S}"
            decision_incident = self._incident_id
            transition = Transition.ALERT_OPENED
            status = DetectionStatus.SPILL_DETECTED
        else:
            status = DetectionStatus.SUSPECTED if raw_positive else DetectionStatus.NORMAL

        return EventDecision(
            status=status,
            transition=transition,
            raw_positive=raw_positive,
            positive_count=sum(self._window),
            window_size=len(self._window),
            incident_id=decision_incident,
            occurred_at=occurred_at,
        )

    @property
    def incident_id(self) -> str | None:
        return self._incident_id

    @property
    def event_open(self) -> bool:
        return self._event_open

    def restore_active_incident(self, incident_id: str) -> None:
        """Resume an incident after a service restart without opening a duplicate."""
        if not incident_id:
            raise ValueError("incident_id tidak boleh kosong")
        self._event_open = True
        self._incident_id = incident_id
        self._negative_streak = 0
        self._window.clear()
