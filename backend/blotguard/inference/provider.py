"""Lazy, process-local model provider used by the analysis service."""

from __future__ import annotations

import hashlib
from pathlib import Path
from threading import Lock

from backend.blotguard.core.config import RuntimeConfig
from backend.blotguard.domain.contracts import DetectionResult, ModelMetadata


class ModelUnavailableError(RuntimeError):
    """Raised when configured model assets or runtime dependencies are absent."""


class MockDetector:
    """Deterministic development-only detector, never enabled implicitly."""

    def predict(self, image_path: str | Path) -> DetectionResult:
        digest = hashlib.sha256(Path(image_path).read_bytes()).digest()
        score = int.from_bytes(digest[:2], "big") / 65535
        return DetectionResult(
            prediction="generated" if score > 0.5 else "original",
            score_generated=score,
            threshold=0.5,
            model=ModelMetadata(
                name="development-mock-detector",
                version="mock-v1",
                weight_sha256="not-a-real-model",
                threshold=0.5,
                runtime="deterministic-hash:cpu",
                is_mock=True,
            ),
        )


class InferenceProvider:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._detector = None
        self._lock = Lock()

    def readiness(self) -> tuple[bool, list[str]]:
        if self.config.inference_mode == "mock":
            return True, ["mock inference is enabled"]
        missing = self.config.detector.missing_assets()
        if missing:
            return False, [f"missing model asset: {path}" for path in missing]
        try:
            import cv2  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            return False, [f"missing model runtime dependency: {exc.name}"]
        return True, []

    def detector(self):
        if self._detector is not None:
            return self._detector
        with self._lock:
            if self._detector is not None:
                return self._detector
            if self.config.inference_mode == "mock":
                self._detector = MockDetector()
                return self._detector

            ready, reasons = self.readiness()
            if not ready:
                raise ModelUnavailableError("; ".join(reasons))
            from .detector import Detector

            self._detector = Detector(
                self.config.detector, device=self.config.device
            )
            return self._detector
