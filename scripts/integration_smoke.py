from __future__ import annotations

import argparse
import faulthandler
import json
import os
import time
from pathlib import Path


def main() -> None:
    faulthandler.dump_traceback_later(25, repeat=False)
    parser = argparse.ArgumentParser(description="End-to-end smoke test tanpa cloud")
    parser.add_argument("--model", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--seconds", type=int, default=8)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    work = root / "data" / "smoke"
    work.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        {
            "APP_ENV": "development",
            "VIDEO_SOURCE_TYPE": "file",
            "VIDEO_FILE_PATH": str(Path(args.video).resolve()),
            "VIDEO_LOOP": "true",
            "INFERENCE_BACKEND": "onnx",
            "ONNX_MODEL_PATH": str(Path(args.model).resolve()),
            "FIREBASE_ENABLED": "false",
            "TELEGRAM_ENABLED": "false",
            "API_KEY": "",
            "TIMEZONE": "Asia/Singapore",
            "SQLITE_PATH": str(work / "smoke.db"),
            "EVIDENCE_DIRECTORY": str(work / "evidence"),
            "LOG_DIRECTORY": str(work / "logs"),
            "INFERENCE_INTERVAL_SECONDS": "1",
        }
    )

    from app.camera import CameraManager
    from app.config import Settings
    from app.event_engine import EventEngine
    from app.evidence import EvidenceManager
    from app.inference.onnx_engine import OnnxEngine
    from app.storage import Storage

    settings = Settings.from_env()
    settings.ensure_directories()
    print("SMOKE: settings loaded", flush=True)
    camera = CameraManager(settings)
    engine = OnnxEngine(
        settings.onnx_model_path,
        settings.model_input_width,
        settings.model_input_height,
        settings.pixel_threshold,
        settings.roi_polygon,
        settings.onnx_intra_op_threads,
        settings.onnx_inter_op_threads,
    )
    event_engine = EventEngine(
        settings.temporal_window_size,
        settings.positive_required,
        settings.negative_to_clear,
    )
    evidence = EvidenceManager(settings)
    storage = Storage(settings.sqlite_path)
    camera.start()
    print("SMOKE: core components started", flush=True)

    started = time.monotonic()
    last_frame_id = -1
    last_inference = 0.0
    processed = 0
    latest = None
    try:
        while time.monotonic() - started < args.seconds:
            packet = camera.latest()
            now = time.monotonic()
            if (
                packet is None
                or packet.frame_id == last_frame_id
                or now - last_inference < settings.inference_interval_seconds
            ):
                time.sleep(0.05)
                continue
            last_frame_id = packet.frame_id
            last_inference = now
            result = engine.infer(packet.frame)
            decision = event_engine.update(
                result.area_ratio >= settings.area_threshold,
                packet.captured_at,
            )
            latest = (result, decision)
            processed += 1
            if decision.transition.value == "ALERT_OPENED" and decision.incident_id:
                paths = evidence.save(
                    packet.frame,
                    result,
                    decision.incident_id,
                    packet.captured_at,
                )
                storage.record_event(
                    {
                        "eventId": f"smoke-{decision.incident_id}",
                        "timestampMs": int(packet.captured_at.timestamp() * 1000),
                        "cameraId": settings.camera_id,
                        "type": "INCIDENT_OPENED",
                        "status": decision.status.value,
                        "confidence": result.confidence,
                        "predictedAreaRatio": result.area_ratio,
                        "incidentId": decision.incident_id,
                        "message": "Smoke test incident",
                        "snapshotPath": paths.get("overlay") or paths.get("raw"),
                    }
                )
    finally:
        camera.stop()

    if latest is None:
        storage.close()
        raise SystemExit("Smoke test gagal: tidak ada frame yang berhasil diproses")
    result, decision = latest
    report = {
        "health": {
            "systemStatus": "ONLINE",
            "cameraStatus": camera.status,
            "inferenceStatus": "RUNNING",
            "detectionStatus": decision.status.value,
            "processedFrames": processed,
            "inferenceMs": round(result.inference_ms, 2),
            "predictedAreaRatio": result.area_ratio,
            "incidentId": event_engine.incident_id,
        },
        "events": storage.recent_events(limit=20),
    }
    storage.close()
    try:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report["health"]["systemStatus"] != "ONLINE":
            raise SystemExit("Smoke test gagal: sistem tidak ONLINE")
        if report["health"]["inferenceStatus"] != "RUNNING":
            raise SystemExit("Smoke test gagal: inference tidak RUNNING")
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    main()
