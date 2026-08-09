#!/usr/bin/env python
"""Calibrate detector scores and freeze diagnostic thresholds on calibration data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import GroupKFold
from sklearn.utils.class_weight import compute_sample_weight


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.detector_metrics import metrics_at_threshold


RISK_TARGETS = (0.10, 0.30, 0.70, 0.90)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weighted_ece(
    labels: np.ndarray,
    probabilities: np.ndarray,
    weights: np.ndarray,
    bins: int = 10,
) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total_weight = float(weights.sum())
    value = 0.0
    for index in range(bins):
        lower, upper = edges[index], edges[index + 1]
        mask = (
            (probabilities >= lower) & (probabilities <= upper)
            if index == bins - 1
            else (probabilities >= lower) & (probabilities < upper)
        )
        if not mask.any():
            continue
        bin_weight = float(weights[mask].sum())
        observed = float(np.average(labels[mask], weights=weights[mask]))
        predicted = float(np.average(probabilities[mask], weights=weights[mask]))
        value += bin_weight / total_weight * abs(observed - predicted)
    return value


def calibration_metrics(
    labels: np.ndarray, probabilities: np.ndarray, weights: np.ndarray
) -> dict[str, float]:
    clipped = np.clip(probabilities, 1e-7, 1 - 1e-7)
    return {
        "weighted_brier": float(
            brier_score_loss(labels, clipped, sample_weight=weights)
        ),
        "weighted_log_loss": float(
            log_loss(labels, clipped, sample_weight=weights, labels=[0, 1])
        ),
        "weighted_ece_10_bins": weighted_ece(labels, clipped, weights),
    }


def wilson_interval(successes: int, total: int, z: float = 1.96) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        rate * (1 - rate) / total + z * z / (4 * total * total)
    ) / denominator
    return [center - margin, center + margin]


def inverse_platt_target(coefficient: float, intercept: float, target: float) -> float:
    target_logit = math.log(target / (1 - target))
    raw_logit = (target_logit - intercept) / coefficient
    return 1 / (1 + math.exp(-raw_logit))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-fpr", type=float, default=0.05)
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    with input_path.open(newline="", encoding="utf-8") as stream:
        samples = list(csv.DictReader(stream))
    if not samples or {row["split"] for row in samples} != {"calibration"}:
        raise ValueError("Input must contain only calibration rows")

    labels = np.array(
        [row["expected_source_class"] == "generated" for row in samples], dtype=int
    )
    scores = np.array([float(row["score_generated"]) for row in samples])
    logits = np.array([float(row["logit"]) for row in samples])
    groups = np.array([row["family_id"] for row in samples])
    weights = compute_sample_weight(class_weight="balanced", y=labels)

    splitter = GroupKFold(n_splits=5)
    platt_oof = np.zeros_like(scores)
    isotonic_oof = np.zeros_like(scores)
    for train_indices, validation_indices in splitter.split(scores, labels, groups):
        platt = LogisticRegression(C=1_000_000, solver="lbfgs")
        platt.fit(
            logits[train_indices, None],
            labels[train_indices],
            sample_weight=weights[train_indices],
        )
        platt_oof[validation_indices] = platt.predict_proba(
            logits[validation_indices, None]
        )[:, 1]

        isotonic = IsotonicRegression(out_of_bounds="clip")
        isotonic.fit(
            scores[train_indices],
            labels[train_indices],
            sample_weight=weights[train_indices],
        )
        isotonic_oof[validation_indices] = isotonic.predict(scores[validation_indices])

    method_metrics = {
        "uncalibrated_sigmoid": calibration_metrics(labels, scores, weights),
        "platt": calibration_metrics(labels, platt_oof, weights),
        "isotonic": calibration_metrics(labels, isotonic_oof, weights),
    }
    platt_metrics = method_metrics["platt"]
    isotonic_metrics = method_metrics["isotonic"]
    selected_method = (
        "isotonic"
        if isotonic_metrics["weighted_brier"]
        <= platt_metrics["weighted_brier"] - 0.005
        and isotonic_metrics["weighted_log_loss"]
        <= platt_metrics["weighted_log_loss"]
        else "platt"
    )

    if selected_method == "platt":
        final_model = LogisticRegression(C=1_000_000, solver="lbfgs")
        final_model.fit(logits[:, None], labels, sample_weight=weights)
        coefficient = float(final_model.coef_[0, 0])
        intercept = float(final_model.intercept_[0])
        calibrator = {
            "method": "platt",
            "input": "raw_logit",
            "coefficient": coefficient,
            "intercept": intercept,
        }
        risk_boundaries = [
            inverse_platt_target(coefficient, intercept, target)
            for target in RISK_TARGETS
        ]
    else:
        final_model = IsotonicRegression(out_of_bounds="clip")
        final_model.fit(scores, labels, sample_weight=weights)
        calibrator = {
            "method": "isotonic",
            "input": "uncalibrated_sigmoid_score",
            "x_thresholds": [float(value) for value in final_model.X_thresholds_],
            "y_thresholds": [float(value) for value in final_model.y_thresholds_],
        }
        candidates = np.unique(scores)
        calibrated = final_model.predict(candidates)
        risk_boundaries = []
        for target in RISK_TARGETS:
            index = min(
                int(np.searchsorted(calibrated, target, side="left")),
                len(candidates) - 1,
            )
            risk_boundaries.append(float(candidates[index]))

    threshold_candidates = sorted({0.0, 0.5, 1.0, *scores.tolist()})
    operating_points = []
    for threshold in threshold_candidates:
        metrics = metrics_at_threshold(samples, threshold)
        if float(metrics["false_positive_rate"]) <= args.max_fpr:
            operating_points.append((threshold, metrics))
    selected_threshold, selected_metrics = max(
        operating_points,
        key=lambda item: (
            float(item[1]["f1"]),
            float(item[1]["balanced_accuracy"]),
            item[0],
        ),
    )

    group_metrics = {}
    for group in ("real", "cyclegan", "ddpm", "pix2pix", "stylegan2ada"):
        group_rows = [
            row for row in samples if (row["generator"] or "real") == group
        ]
        expected_generated = group != "real"
        successes = sum(
            (float(row["score_generated"]) > selected_threshold)
            == expected_generated
            for row in group_rows
        )
        group_metrics[group] = {
            "correct": successes,
            "total": len(group_rows),
            "rate": successes / len(group_rows),
            "wilson_95": wilson_interval(successes, len(group_rows)),
        }

    acceptance = {
        "false_positive_rate_lte_0_05": float(
            selected_metrics["false_positive_rate"]
        )
        <= 0.05,
        "overall_f1_gte_0_90": float(selected_metrics["f1"]) >= 0.90,
        "ddpm_recall_gte_0_80": group_metrics["ddpm"]["rate"] >= 0.80,
        "cyclegan_recall_gte_0_90": group_metrics["cyclegan"]["rate"] >= 0.90,
        "pix2pix_recall_gte_0_90": group_metrics["pix2pix"]["rate"] >= 0.90,
        "stylegan2ada_recall_gte_0_90": group_metrics["stylegan2ada"]["rate"]
        >= 0.90,
    }
    passed = all(acceptance.values())

    output = {
        "schema_version": 1,
        "status": "passed" if passed else "blocked_model_quality",
        "deployable": passed,
        "test_evaluation_authorized": passed,
        "source_predictions": (
            input_path.relative_to(ROOT).as_posix()
            if input_path.is_relative_to(ROOT)
            else str(input_path)
        ),
        "source_predictions_sha256": sha256(input_path),
        "sample_count": len(samples),
        "class_counts": {
            "original": int((labels == 0).sum()),
            "generated": int((labels == 1).sum()),
        },
        "weighting": "balanced classes; calibrated risk is not deployment prevalence",
        "cross_validation": {
            "strategy": "5-fold GroupKFold by family_id",
            "method_metrics": method_metrics,
            "selection_rule": (
                "isotonic only if weighted Brier improves by at least 0.005 and "
                "weighted log loss does not worsen; otherwise Platt"
            ),
            "selected_method": selected_method,
        },
        "calibrator": calibrator,
        "five_level_policy": {
            "semantics": "class_balanced_calibrated_risk; not real-world probability",
            "calibrated_risk_targets": list(RISK_TARGETS),
            "raw_score_boundaries": risk_boundaries,
            "levels": ["very_low", "low", "medium", "high", "very_high"],
            "deployable": passed,
        },
        "binary_threshold": {
            "selection_objective": (
                "maximize F1, then balanced accuracy, under FPR <= 0.05"
            ),
            "raw_score_threshold": selected_threshold,
            "metrics": selected_metrics,
            "group_metrics": group_metrics,
            "deployable": passed,
        },
        "current_binary_threshold": {
            "raw_score_threshold": 0.5,
            "metrics": metrics_at_threshold(samples, 0.5),
        },
        "acceptance": acceptance,
        "warning": (
            None
            if passed
            else "Calibration failed frozen quality gates; keep test sealed and do not deploy thresholds."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
