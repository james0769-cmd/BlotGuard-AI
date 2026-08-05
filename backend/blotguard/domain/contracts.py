"""Stable domain and wire contracts for analysis tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


SCORE_SEMANTICS = "uncalibrated_sigmoid_risk_score"


def device_from_runtime(runtime: str) -> str:
    _, separator, device = runtime.partition(":")
    return device if separator else runtime


class TaskStatus(str, Enum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    INFERENCING = "inferencing"
    REPORTING = "reporting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        return self.value


class ItemStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


TERMINAL_TASK_STATUSES = {
    TaskStatus.SUCCEEDED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    version: str
    weight_sha256: str
    threshold: float
    runtime: str
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "device": self.device}

    @property
    def device(self) -> str:
        return device_from_runtime(self.runtime)


@dataclass(frozen=True)
class DetectionResult:
    prediction: str
    score_generated: float
    threshold: float
    model: ModelMetadata
    logit: float | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": "detect",
            "device": self.model.device,
            "logit": self.logit,
            "score_generated": self.score_generated,
            "score_semantics": SCORE_SEMANTICS,
            "prediction": self.prediction,
            "threshold": self.threshold,
            "model_name": self.model.name,
            "model_version": self.model.version,
            "weight_sha256": self.model.weight_sha256,
            "is_mock": self.model.is_mock,
        }


@dataclass(frozen=True)
class LocalizationResult:
    mask_path: str
    mask_width: int
    mask_height: int
    mask_coverage: float
    model: ModelMetadata


@dataclass(frozen=True)
class ExtractedImage:
    path: str
    source_name: str
    source_index: int
    page_number: int | None
    width: int
    height: int
    sha256: str
