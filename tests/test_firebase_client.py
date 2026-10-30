from app.firebase_client import FirebaseClient


def test_public_payload_removes_local_file_paths() -> None:
    payload = {
        "eventId": "event-1",
        "snapshotPath": "/opt/data/overlay.jpg",
        "rawSnapshotPath": "/opt/data/raw.jpg",
        "overlaySnapshotPath": "/opt/data/overlay.jpg",
        "status": "TUMPAHAN_TERDETEKSI",
    }

    assert FirebaseClient._public_payload(payload) == {
        "eventId": "event-1",
        "status": "TUMPAHAN_TERDETEKSI",
    }
