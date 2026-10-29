from app.storage import Storage


def test_event_and_sync_queue_are_persistent(tmp_path) -> None:
    storage = Storage(tmp_path / "monitor.db")
    payload = {
        "eventId": "event-1",
        "timestampMs": 1234,
        "cameraId": "cam-01",
        "type": "INCIDENT_OPENED",
        "status": "TUMPAHAN_TERDETEKSI",
        "confidence": 0.91,
        "predictedAreaRatio": 0.02,
        "incidentId": "OS-1",
        "message": "test",
        "snapshotPath": None,
    }
    storage.record_event(payload)
    storage.enqueue("firebase_event", "event-1", payload, 1234)

    assert storage.recent_events()[0]["eventId"] == "event-1"
    due = storage.due_items(1234)
    assert len(due) == 1
    assert due[0]["payload"]["incidentId"] == "OS-1"

    storage.mark_done(due[0]["id"])
    assert storage.queue_size() == 0
    storage.close()


def test_live_queue_keeps_only_latest_payload(tmp_path) -> None:
    storage = Storage(tmp_path / "monitor.db")
    storage.enqueue("firebase_live", "live_status", {"value": 1}, 100)
    storage.enqueue("firebase_live", "live_status", {"value": 2}, 200)
    items = storage.due_items(200)
    assert len(items) == 1
    assert items[0]["payload"]["value"] == 2
    storage.close()
