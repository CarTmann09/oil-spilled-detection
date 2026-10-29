from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from ..domain import InferenceResult
from .base import InferenceEngine

MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


class OnnxEngine(InferenceEngine):
    def __init__(
        self,
        model_path: Path,
        width: int,
        height: int,
        pixel_threshold: float,
        roi_polygon: tuple[tuple[float, float], ...] = (),
        intra_op_threads: int = 4,
        inter_op_threads: int = 1,
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model ONNX tidak ditemukan: {model_path}")
        self.width = width
        self.height = height
        self.pixel_threshold = pixel_threshold

        options = ort.SessionOptions()
        options.intra_op_num_threads = intra_op_threads
        options.inter_op_num_threads = inter_op_threads
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.roi_mask = self._create_roi_mask(roi_polygon)

    @property
    def backend_name(self) -> str:
        return "ONNXRuntime-CPU"

    def _create_roi_mask(
        self, points: tuple[tuple[float, float], ...]
    ) -> np.ndarray:
        mask = np.ones((self.height, self.width), dtype=bool)
        if not points:
            return mask
        mask[:] = False
        polygon = np.asarray(
            [[round(x * (self.width - 1)), round(y * (self.height - 1))] for x, y in points],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [polygon], 1)
        return mask

    def infer(self, frame: np.ndarray) -> InferenceResult:
        resized = cv2.resize(
            frame, (self.width, self.height), interpolation=cv2.INTER_AREA
        )
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        normalized = (rgb - MEAN) / STD
        tensor = np.ascontiguousarray(normalized.transpose(2, 0, 1)[None, ...])

        started = time.perf_counter()
        logits = self.session.run([self.output_name], {self.input_name: tensor})[0]
        inference_ms = (time.perf_counter() - started) * 1000

        logits_2d = np.asarray(logits)[0, 0]
        probability = 1.0 / (1.0 + np.exp(-np.clip(logits_2d, -50, 50)))
        predicted = (probability >= self.pixel_threshold) & self.roi_mask

        # Denominator tetap seluruh frame agar threshold area konsisten dengan validasi model.
        area_ratio = float(predicted.mean())
        roi_values = probability[self.roi_mask]
        max_probability = float(roi_values.max()) if roi_values.size else 0.0
        mean_probability = (
            float(probability[predicted].mean()) if predicted.any() else 0.0
        )
        return InferenceResult(
            mask=predicted,
            area_ratio=area_ratio,
            max_probability=max_probability,
            mean_mask_probability=mean_probability,
            inference_ms=inference_ms,
        )
