from app.monitor import OilSpillMonitor


def _normal_state() -> dict[str, object]:
    return {
        "detectionStatus": "NORMAL",
        "incidentId": None,
        "cameraStatus": "CONNECTED",
        "inferenceStatus": "RUNNING",
    }


def test_daily_normal_allowed_when_day_has_no_spill() -> None:
    assert OilSpillMonitor._should_send_daily_normal(
        _normal_state(), had_spill_today=False
    )


def test_daily_normal_suppressed_when_spill_occurred_today() -> None:
    assert not OilSpillMonitor._should_send_daily_normal(
        _normal_state(), had_spill_today=True
    )


def test_daily_normal_requires_healthy_current_state() -> None:
    state = _normal_state()
    state["cameraStatus"] = "RECONNECTING"
    assert not OilSpillMonitor._should_send_daily_normal(
        state, had_spill_today=False
    )
