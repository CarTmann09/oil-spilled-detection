from __future__ import annotations

from typing import Any

from .config import Settings


class FirebaseClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.firebase_enabled
        self._db = None
        if not self.enabled:
            return

        import firebase_admin
        from firebase_admin import credentials, db

        try:
            firebase_admin.get_app()
        except ValueError:
            credential = credentials.Certificate(
                str(settings.google_application_credentials)
            )
            firebase_admin.initialize_app(
                credential, {"databaseURL": settings.firebase_database_url}
            )
        self._db = db

    def set_live(self, payload: dict[str, Any]) -> None:
        if not self.enabled or self._db is None:
            return
        self._db.reference(self.settings.firebase_live_path.strip("/")).set(payload)

    def set_event(self, payload: dict[str, Any]) -> None:
        if not self.enabled or self._db is None:
            return
        event_id = str(payload["eventId"])
        public_payload = {k: v for k, v in payload.items() if k != "snapshotPath"}
        base = self.settings.firebase_event_log_path.strip("/")
        path = f"{base}/{event_id}"
        self._db.reference(path).set(public_payload)

    def set_incident(self, payload: dict[str, Any]) -> None:
        if not self.enabled or self._db is None:
            return
        incident_id = str(payload["incidentId"])
        public_payload = {k: v for k, v in payload.items() if k != "snapshotPath"}
        base = self.settings.firebase_incident_path.strip("/")
        path = f"{base}/{incident_id}"
        self._db.reference(path).update(public_payload)
