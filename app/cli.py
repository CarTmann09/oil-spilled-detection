from __future__ import annotations

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

from .camera import CameraManager
from .config import Settings
from .inference.onnx_engine import OnnxEngine


def load_settings(path: str) -> Settings:
    return Settings.from_env(path)


def validate(settings: Settings) -> int:
    model_exists = settings.onnx_model_path.exists()
    source_exists = (
        True
        if settings.video_source_type == "rtsp"
        else settings.video_file_path.exists()
    )
    report = {
        "configuration": "OK",
        "videoSourceType": settings.video_source_type,
        "sourceConfigured": source_exists,
        "modelPath": str(settings.onnx_model_path),
        "modelExists": model_exists,
        "firebaseEnabled": settings.firebase_enabled,
        "telegramEnabled": settings.telegram_enabled,
    }
    print(json.dumps(report, indent=2))
    return 0 if model_exists and source_exists else 1


def check_model(settings: Settings) -> int:
    engine = OnnxEngine(
        settings.onnx_model_path,
        settings.model_input_width,
        settings.model_input_height,
        settings.pixel_threshold,
        settings.roi_polygon,
        settings.onnx_intra_op_threads,
        settings.onnx_inter_op_threads,
    )
    dummy = np.zeros(
        (settings.model_input_height, settings.model_input_width, 3), dtype=np.uint8
    )
    result = engine.infer(dummy)
    print(
        json.dumps(
            {
                "backend": engine.backend_name,
                "inferenceMs": round(result.inference_ms, 2),
                "outputShape": list(result.mask.shape),
                "areaRatio": result.area_ratio,
                "status": "OK",
            },
            indent=2,
        )
    )
    return 0


def check_camera(settings: Settings, timeout: int) -> int:
    camera = CameraManager(settings)
    camera.start()
    deadline = time.monotonic() + timeout
    packet = None
    while time.monotonic() < deadline:
        packet = camera.latest()
        if packet is not None:
            break
        time.sleep(0.2)
    camera.stop()
    if packet is None:
        print(json.dumps({"status": "ERROR", "camera": camera.status}))
        return 1
    output = settings.sqlite_path.parent / "camera-check.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), packet.frame)
    print(
        json.dumps(
            {
                "status": "OK",
                "width": int(packet.frame.shape[1]),
                "height": int(packet.frame.shape[0]),
                "snapshot": str(output),
            },
            indent=2,
        )
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Oil Spill Monitoring tools")
    parser.add_argument(
        "--env", default=os.getenv("ENV_FILE", ".env"), help="Path file .env"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("check-model")
    camera_parser = subparsers.add_parser("check-camera")
    camera_parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    try:
        settings = load_settings(args.env)
        if args.command == "validate":
            code = validate(settings)
        elif args.command == "check-model":
            code = check_model(settings)
        else:
            code = check_camera(settings, args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}, indent=2))
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
