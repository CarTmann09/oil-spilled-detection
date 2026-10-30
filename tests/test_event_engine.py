from datetime import UTC, datetime, timedelta

from app.domain import DetectionStatus, Transition
from app.event_engine import EventEngine


def test_opens_after_three_of_five_and_closes_after_five_negative() -> None:
    engine = EventEngine(temporal_window=5, positive_required=3, negative_to_clear=5)
    start = datetime(2026, 10, 29, tzinfo=UTC)
    decisions = [
        engine.update(value, start + timedelta(seconds=index))
        for index, value in enumerate([True, False, True, False, True])
    ]

    opened = decisions[-1]
    assert opened.transition == Transition.ALERT_OPENED
    assert opened.status == DetectionStatus.SPILL_DETECTED
    assert opened.incident_id is not None
    assert engine.event_open

    for index in range(4):
        decision = engine.update(False, start + timedelta(seconds=6 + index))
        assert decision.transition == Transition.NONE
        assert decision.status == DetectionStatus.SPILL_DETECTED

    closed = engine.update(False, start + timedelta(seconds=10))
    assert closed.transition == Transition.ALERT_CLOSED
    assert closed.status == DetectionStatus.NORMAL
    assert closed.incident_id == opened.incident_id
    assert not engine.event_open


def test_short_positive_does_not_open_event() -> None:
    engine = EventEngine(temporal_window=5, positive_required=3, negative_to_clear=5)
    start = datetime(2026, 10, 29, tzinfo=UTC)
    values = [False, True, False, True, False, False]
    decisions = [
        engine.update(value, start + timedelta(seconds=index))
        for index, value in enumerate(values)
    ]
    assert all(item.transition == Transition.NONE for item in decisions)
    assert not engine.event_open


def test_restored_incident_does_not_open_duplicate_alert() -> None:
    engine = EventEngine(temporal_window=5, positive_required=3, negative_to_clear=5)
    engine.restore_active_incident("OS-20261030-120000")
    now = datetime(2026, 10, 30, 12, 5, tzinfo=UTC)

    still_open = engine.update(True, now)
    assert still_open.transition == Transition.NONE
    assert still_open.incident_id == "OS-20261030-120000"
    assert engine.event_open

    for index in range(4):
        decision = engine.update(False, now + timedelta(seconds=index + 1))
        assert decision.transition == Transition.NONE

    closed = engine.update(False, now + timedelta(seconds=5))
    assert closed.transition == Transition.ALERT_CLOSED
    assert closed.incident_id == "OS-20261030-120000"
