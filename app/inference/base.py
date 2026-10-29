from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..domain import InferenceResult


class InferenceEngine(ABC):
    @abstractmethod
    def infer(self, frame: np.ndarray) -> InferenceResult:
        raise NotImplementedError

    @property
    @abstractmethod
    def backend_name(self) -> str:
        raise NotImplementedError
