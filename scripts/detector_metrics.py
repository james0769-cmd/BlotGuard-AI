"""Pure metric helpers shared by detector evaluation scripts."""

from __future__ import annotations


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def binary_metrics(
    true_positive: int,
    true_negative: int,
    false_positive: int,
    false_negative: int,
) -> dict[str, float | int]:
    total = true_positive + true_negative + false_positive + false_negative
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    specificity = _ratio(true_negative, true_negative + false_positive)
    return {
        "correct": true_positive + true_negative,
        "total": total,
        "accuracy": _ratio(true_positive + true_negative, total),
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * precision * recall, precision + recall),
        "specificity": specificity,
        "false_positive_rate": _ratio(false_positive, true_negative + false_positive),
        "false_negative_rate": _ratio(false_negative, true_positive + false_negative),
        "balanced_accuracy": (recall + specificity) / 2,
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def metrics_at_threshold(
    samples: list[dict[str, object]], threshold: float
) -> dict[str, float | int]:
    true_positive = true_negative = false_positive = false_negative = 0
    for sample in samples:
        expected_generated = sample["expected_source_class"] == "generated"
        predicted_generated = float(sample["score_generated"]) > threshold
        if expected_generated and predicted_generated:
            true_positive += 1
        elif not expected_generated and not predicted_generated:
            true_negative += 1
        elif predicted_generated:
            false_positive += 1
        else:
            false_negative += 1
    return binary_metrics(
        true_positive, true_negative, false_positive, false_negative
    )
