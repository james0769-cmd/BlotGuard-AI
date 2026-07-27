"""Stable domain and wire contracts for analysis tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


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
        return asdict(self)


@dataclass(frozen=True)
class DetectionResult:
    prediction: str
    score_generated: float
    threshold: float
    model: ModelMetadata
    logit: float | None = field(default=None, repr=False)


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
