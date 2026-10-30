from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any


class Storage:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    timestamp_ms INTEGER NOT NULL,
                    camera_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    predicted_area_ratio REAL NOT NULL,
                    incident_id TEXT,
                    message TEXT NOT NULL,
                    snapshot_path TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp_ms DESC);

                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    unique_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_ms INTEGER NOT NULL,
                    last_error TEXT,
                    UNIQUE(channel, unique_key)
                );

                CREATE INDEX IF NOT EXISTS idx_sync_due
                ON sync_queue(next_attempt_ms, id);

                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def record_event(self, payload: dict[str, Any]) -> str:
        event_id = str(payload.get("eventId") or uuid.uuid4())
        payload = {**payload, "eventId": event_id}
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO events (
                    event_id, timestamp_ms, camera_id, type, status, confidence,
                    predicted_area_ratio, incident_id, message, snapshot_path,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    int(payload["timestampMs"]),
                    str(payload["cameraId"]),
                    str(payload["type"]),
                    str(payload["status"]),
                    float(payload.get("confidence", 0)),
                    float(payload.get("predictedAreaRatio", 0)),
                    payload.get("incidentId"),
                    str(payload.get("message", "")),
                    payload.get("snapshotPath"),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
        return event_id

    def enqueue(
        self,
        channel: str,
        unique_key: str,
        payload: dict[str, Any],
        now_ms: int,
    ) -> None:
        serialized = json.dumps(payload, ensure_ascii=False)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sync_queue (
                    channel, unique_key, payload_json, created_at_ms, next_attempt_ms
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel, unique_key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    next_attempt_ms=excluded.next_attempt_ms,
                    last_error=NULL
                """,
                (channel, unique_key, serialized, now_ms, now_ms),
            )

    def due_items(self, now_ms: int, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM sync_queue
                WHERE next_attempt_ms <= ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (now_ms, limit),
            ).fetchall()
        return [
            {**dict(row), "payload": json.loads(row["payload_json"])} for row in rows
        ]

    def mark_done(self, queue_id: int) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM sync_queue WHERE id=?", (queue_id,))

    def mark_failed(
        self,
        queue_id: int,
        attempts: int,
        error: str,
        now_ms: int,
        base_delay_seconds: int,
        max_delay_seconds: int,
    ) -> None:
        next_attempt = now_ms + min(
            max_delay_seconds, base_delay_seconds * (2 ** min(attempts, 5))
        ) * 1000
        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE sync_queue
                SET attempts=?, next_attempt_ms=?, last_error=?
                WHERE id=?
                """,
                (attempts, next_attempt, error[:1000], queue_id),
            )

    def recent_events(self, limit: int = 50, before_ms: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM events"
        parameters: list[Any] = []
        if before_ms is not None:
            query += " WHERE timestamp_ms < ?"
            parameters.append(before_ms)
        query += " ORDER BY timestamp_ms DESC LIMIT ?"
        parameters.append(min(max(limit, 1), 200))
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def event_exists_between(
        self, event_type: str, start_ms: int, end_ms: int
    ) -> bool:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1 FROM events
                WHERE type=? AND timestamp_ms>=? AND timestamp_ms<?
                LIMIT 1
                """,
                (event_type, start_ms, end_ms),
            ).fetchone()
        return row is not None

    def active_incident(self) -> dict[str, Any] | None:
        """Return the newest incident that has no matching close event."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT opened.payload_json
                FROM events AS opened
                WHERE opened.type='INCIDENT_OPENED'
                  AND opened.incident_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM events AS closed
                    WHERE closed.type='INCIDENT_CLOSED'
                      AND closed.incident_id=opened.incident_id
                  )
                ORDER BY opened.timestamp_ms DESC
                LIMIT 1
                """
            ).fetchone()
        return None if row is None else json.loads(row["payload_json"])

    def set_metadata(self, key: str, value: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO metadata(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )

    def get_metadata(self, key: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM metadata WHERE key=?", (key,)
            ).fetchone()
        return None if row is None else str(row["value"])

    def queue_size(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS count FROM sync_queue"
            ).fetchone()
        return int(row["count"])
