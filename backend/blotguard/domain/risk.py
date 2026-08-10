"""Experimental five-level risk mapping for detector scores."""

from __future__ import annotations

from typing import Literal


RiskLevel = Literal["very_low", "low", "medium", "high", "very_high"]

RISK_LEVEL_BOUNDARIES = (
    0.11865540902281878,
    0.237057370700807,
    0.47028575870349404,
    0.6720226014610423,
)
RISK_LEVEL_SEMANTICS = "experimental_class_balanced_calibrated_risk"
RISK_LEVEL_VERSION = "experimental-platt-balanced-v1"
RISK_LEVEL_LABELS: dict[RiskLevel, str] = {
    "very_low": "极低风险",
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "very_high": "极高风险",
}


def risk_level_for_score(score: float | None) -> RiskLevel | None:
    if score is None:
        return None
    if score < RISK_LEVEL_BOUNDARIES[0]:
        return "very_low"
    if score < RISK_LEVEL_BOUNDARIES[1]:
        return "low"
    if score < RISK_LEVEL_BOUNDARIES[2]:
        return "medium"
    if score < RISK_LEVEL_BOUNDARIES[3]:
        return "high"
    return "very_high"
