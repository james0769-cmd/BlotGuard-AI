#!/usr/bin/env python
"""Run detector smoke inference on one image or the fixed sample dataset."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_DATASET = ROOT / "sample_data" / "western_blots_dataset"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".jfif", ".png", ".tif", ".tiff"}


def _relative_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _discover_images(dataset: Path) -> list[Path]:
    if not dataset.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {dataset}")
    images = sorted(
        path
        for path in dataset.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise FileNotFoundError(f"No images found under dataset: {dataset}")
    return images


def _sample_group(path: Path, dataset: Path | None) -> str | None:
    if dataset is None:
        return None
    try:
        parts = path.resolve().relative_to(dataset.resolve()).parts
    except ValueError:
        return None
    if parts and parts[0] == "synth" and len(parts) > 1:
        return f"synth/{parts[1]}"
    return parts[0] if parts else None


def _run_detector(detector, images: Iterable[Path], dataset: Path | None):
    results = []
    for image_path in images:
        detection = detector.predict(image_path)
        results.append(
            {
                "sample_id": (
                    _relative_path(image_path, dataset)
                    if dataset is not None
                    else image_path.name
                ),
                "path": str(image_path.resolve()),
                "sample_group": _sample_group(image_path, dataset),
                "prediction": detection.prediction,
                "score_generated": detection.score_generated,
                "threshold": detection.threshold,
                "logit": detection.logit,
                "model": detection.model.to_dict(),
            }
        )
    return results


def _build_payload(mode: str, dataset: Path | None, results: list[dict]):
    summary = {
        "total": len(results),
        "generated": sum(1 for item in results if item["prediction"] == "generated"),
        "original": sum(1 for item in results if item["prediction"] == "original"),
    }
    by_group: dict[str, dict[str, int]] = {}
    for item in results:
        group = item["sample_group"] or "single_image"
        current = by_group.setdefault(group, {"total": 0, "generated": 0, "original": 0})
        current["total"] += 1
        current[item["prediction"]] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": mode,
        "dataset": str(dataset.resolve()) if dataset is not None else None,
        "sample_count": len(results),
        "summary": summary,
        "summary_by_group": by_group,
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test the backend detector adapter. By default it runs the "
            "fixed 25-image sample dataset."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("mock", "real"),
        default="real",
        help="mock validates wiring; real calls backend.blotguard.inference.detector.Detector",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional runtime config path. Defaults to configs/default.yaml.",
    )
    parser.add_argument(
        "--device",
        help="Override BLOTGUARD_DEVICE for real inference, for example cpu or cuda.",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Run one image instead of the fixed dataset.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Dataset directory used when --image is omitted.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON results to this path instead of stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    os.environ["BLOTGUARD_INFERENCE_MODE"] = args.mode
    if args.device:
        os.environ["BLOTGUARD_DEVICE"] = args.device

    from backend.blotguard.core.config import load_runtime_config
    from backend.blotguard.inference.provider import (
        InferenceProvider,
        ModelUnavailableError,
    )

    dataset = None if args.image else args.dataset
    images = [args.image] if args.image else _discover_images(args.dataset)

    config = load_runtime_config(args.config)
    provider = InferenceProvider(config)
    try:
        detector = provider.detector()
        payload = _build_payload(
            args.mode,
            dataset,
            _run_detector(detector, images, dataset),
        )
    except ModelUnavailableError as exc:
        print(f"Detector is not available: {exc}", file=sys.stderr)
        print(
            "Run scripts/verify_model_assets.py and install the model extra "
            "before real inference.",
            file=sys.stderr,
        )
        return 2

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"Wrote detector smoke results to {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
