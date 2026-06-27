"""Stable inference interfaces for BlotGuard models."""

from .contracts import DetectionResult, LocalizationResult
from .detector import Detector
from .localizer import Localizer

__all__ = ["DetectionResult", "Detector", "LocalizationResult", "Localizer"]
