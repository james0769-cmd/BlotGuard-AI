#!/usr/bin/env python
"""Analyze detector thresholds from a saved candidate evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from detector_metrics import metrics_at_threshold


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--preprocess-mode", default="stretch")
    parser.add_argument(
        "--dataset-role", choices=("audit", "validation", "test"), required=True
    )
    parser.add_argument("--max-fpr", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    matches = [
        result
        for result in payload["results"]
        if result["name"] == args.candidate
        and result["preprocess_mode"] == args.preprocess_mode
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one matching result, found {len(matches)}")

    result = matches[0]
    samples = result["samples"]
    thresholds = sorted(
        {0.0, 0.5, 1.0, *(float(row["score_generated"]) for row in samples)}
    )
    rows = []
    for threshold in thresholds:
        metrics = metrics_at_threshold(samples, threshold)
        rows.append({"threshold": threshold, **metrics})

    eligible = [
        row for row in rows if float(row["false_positive_rate"]) <= args.max_fpr
    ]
    selected = max(
        eligible,
        key=lambda row: (
            float(row["f1"]),
            float(row["balanced_accuracy"]),
            float(row["threshold"]),
        ),
    )
    current = next(row for row in rows if row["threshold"] == 0.5)
    output = {
        "source_evaluation": str(args.input.resolve()),
        "source_evaluation_sha256": sha256(args.input),
        "source_manifest": payload.get("manifest"),
        "sample_count": payload.get("sample_count"),
        "candidate": args.candidate,
        "weight_sha256": result["weight_sha256"],
        "preprocess_mode": args.preprocess_mode,
        "dataset_role": args.dataset_role,
        "max_false_positive_rate": args.max_fpr,
        "selection_objective": "maximize_f1_then_balanced_accuracy_under_fpr_constraint",
        "eligible_for_config_change": args.dataset_role == "validation",
        "warning": (
            None
            if args.dataset_role == "validation"
            else "Threshold results are diagnostic only; select deployment thresholds on an independent validation set."
        ),
        "current_threshold": current,
        "best_threshold_under_constraint": selected,
        "evaluated_threshold_count": len(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
