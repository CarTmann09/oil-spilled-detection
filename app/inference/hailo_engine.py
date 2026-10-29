from __future__ import annotations

import numpy as np

from ..domain import InferenceResult
from .base import InferenceEngine


class HailoEngine(InferenceEngine):
    """Placeholder backend. Diaktifkan setelah model HEF tervalidasi."""

    def __init__(self, *_args, **_kwargs) -> None:
        raise RuntimeError(
            "Backend Hailo belum diaktifkan. Gunakan INFERENCE_BACKEND=onnx sampai "
            "best_model.hef tersedia dan lolos regression test."
        )

    @property
    def backend_name(self) -> str:
        return "Hailo-8L"

    def infer(self, frame: np.ndarray) -> InferenceResult:
        raise NotImplementedError
