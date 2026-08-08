import pytest

from backend.blotguard.inference.common import resized_dimensions
from scripts.detector_metrics import binary_metrics, metrics_at_threshold


def test_non_square_preprocess_dimensions_are_stable():
    assert resized_dimensions(200, 400, 512, "stretch") == (512, 512)
    assert resized_dimensions(200, 400, 512, "longest_side") == (256, 512)
    assert resized_dimensions(401, 200, 512, "longest_side") == (512, 255)


def test_unknown_preprocess_mode_is_rejected():
    with pytest.raises(ValueError, match="Unsupported preprocess mode"):
        resized_dimensions(200, 400, 512, "unknown")


def test_binary_metrics_reports_operating_characteristics():
    metrics = binary_metrics(8, 9, 1, 2)

    assert metrics["accuracy"] == pytest.approx(0.85)
    assert metrics["precision"] == pytest.approx(8 / 9)
    assert metrics["recall"] == pytest.approx(0.8)
    assert metrics["false_positive_rate"] == pytest.approx(0.1)
    assert metrics["false_negative_rate"] == pytest.approx(0.2)


def test_threshold_rule_matches_runtime_strict_greater_than():
    samples = [
        {"expected_source_class": "generated", "score_generated": 0.5},
        {"expected_source_class": "generated", "score_generated": 0.8},
        {"expected_source_class": "original", "score_generated": 0.5},
        {"expected_source_class": "original", "score_generated": 0.2},
    ]

    metrics = metrics_at_threshold(samples, 0.5)

    assert metrics["true_positive"] == 1
    assert metrics["true_negative"] == 2
    assert metrics["false_positive"] == 0
    assert metrics["false_negative"] == 1
