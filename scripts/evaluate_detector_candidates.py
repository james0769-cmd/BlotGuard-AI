#!/usr/bin/env python
"""Compare Detector weights and preprocessing on the fixed sample manifest."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import gc
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard.core.config import load_runtime_config
from backend.blotguard.inference.detector import Detector
from detector_metrics import binary_metrics


DEFAULT_MANIFEST = (
    ROOT / "sample_data" / "western_blots_dataset" / "sample_manifest.csv"
)
DEFAULT_OUTPUT = ROOT / "var" / "detector_candidate_evaluation.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_candidate(value: str) -> tuple[str, Path, int, tuple[int, ...] | None]:
    try:
        name, raw_path, raw_rank, raw_layers = value.split("|", 3)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "candidate must be NAME|PATH|RANK|LAYERS; LAYERS is all or comma-separated"
        ) from exc
    layers = (
        None
        if raw_layers == "all"
        else tuple(int(layer) for layer in raw_layers.split(","))
    )
    return name, Path(raw_path).expanduser().resolve(), int(raw_rank), layers


def evaluate_candidate(
    candidate: tuple[str, Path, int, tuple[int, ...] | None],
    preprocess_mode: str,
    samples: list[dict[str, str]],
    sample_root: Path,
    device: str,
    quiet: bool,
) -> dict[str, object]:
    name, weight_path, rank, layers = candidate
    weight_sha256 = sha256(weight_path)
    base = load_runtime_config().detector
    config = replace(
        base,
        lora_weight=weight_path,
        rank=rank,
        lora_layers=layers,
        preprocess_mode=preprocess_mode,
        version=f"candidate-{name}-{preprocess_mode}-{weight_sha256[:8]}",
        weight_sha256=weight_sha256,
    )
    detector = Detector(config, device)
    rows: list[dict[str, object]] = []
    for index, sample in enumerate(samples, start=1):
        image_path = sample_root / sample["sample_path"]
        actual_sha256 = sha256(image_path)
        if actual_sha256 != sample["sample_sha256"]:
            raise ValueError(f"Sample SHA-256 mismatch: {sample['sample_path']}")
        result = detector.predict(image_path)
        expected = sample["expected_source_class"]
        rows.append(
            {
                "sample_path": sample["sample_path"],
                "expected_source_class": expected,
                "generator": sample["generator"],
                "prediction": result.prediction,
                "score_generated": result.score_generated,
                "logit": result.logit,
                "correct": result.prediction == expected,
            }
        )
        if not quiet:
            print(
                f"[{name}/{preprocess_mode} {index:02d}/{len(samples)}] "
                f"{sample['sample_path']}",
                flush=True,
            )

    groups: dict[str, dict[str, int | float]] = {}
    for row in rows:
        group = str(row["generator"] or "real")
        totals = groups.setdefault(group, {"correct": 0, "total": 0})
        totals["total"] += 1
        totals["correct"] += int(bool(row["correct"]))
    for totals in groups.values():
        totals["accuracy"] = totals["correct"] / totals["total"]

    true_positive = sum(
        row["expected_source_class"] == "generated"
        and row["prediction"] == "generated"
        for row in rows
    )
    true_negative = sum(
        row["expected_source_class"] == "original"
        and row["prediction"] == "original"
        for row in rows
    )
    false_positive = sum(
        row["expected_source_class"] == "original"
        and row["prediction"] == "generated"
        for row in rows
    )
    false_negative = sum(
        row["expected_source_class"] == "generated"
        and row["prediction"] == "original"
        for row in rows
    )
    del detector
    gc.collect()

    summary = binary_metrics(
        true_positive, true_negative, false_positive, false_negative
    )
    summary["groups"] = groups

    return {
        "name": name,
        "weight_path": str(weight_path),
        "weight_sha256": weight_sha256,
        "rank": rank,
        "lora_layers": "all" if layers is None else list(layers),
        "preprocess_mode": preprocess_mode,
        "threshold": config.threshold,
        "summary": summary,
        "errors": [row for row in rows if not row["correct"]],
        "samples": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate",
        action="append",
        required=True,
        type=parse_candidate,
        help="NAME|PATH|RANK|LAYERS, where LAYERS is all or comma-separated",
    )
    parser.add_argument(
        "--preprocess-mode",
        action="append",
        choices=("stretch", "longest_side"),
        dest="preprocess_modes",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--sample-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as stream:
        samples = list(csv.DictReader(stream))
    if not samples:
        raise ValueError("Manifest contains no samples")

    modes = args.preprocess_modes or ["stretch", "longest_side"]
    results = [
        evaluate_candidate(
            candidate,
            mode,
            samples,
            args.sample_root.expanduser().resolve(),
            args.device,
            args.quiet,
        )
        for candidate in args.candidate
        for mode in modes
    ]
    output = {
        "manifest": str(args.manifest.resolve()),
        "sample_root": str(args.sample_root.expanduser().resolve()),
        "sample_count": len(samples),
        "device": args.device,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
