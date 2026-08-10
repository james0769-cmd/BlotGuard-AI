"""Serializable localization result contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LocalizationResult:
    task: str = field(init=False, default="segment")
    image: str
    device: str
    mask_shape: list[int]
    mask_mean: float
    output: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
