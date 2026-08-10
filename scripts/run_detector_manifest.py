#!/usr/bin/env python
"""Run the frozen Detector over a manifest with batching and resume support."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard.core.config import load_runtime_config
from backend.blotguard.inference.common import load_image
from backend.blotguard.inference.detector import Detector


OUTPUT_FIELDS = (
    "sample_path",
    "sample_sha256",
    "expected_source_class",
    "generator",
    "split",
    "family_id",
    "logit",
    "score_generated",
    "prediction",
    "threshold",
    "model_version",
    "weight_sha256",
    "device",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sample-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise ValueError("batch-size must be at least 1")

    manifest = args.manifest.expanduser().resolve()
    sample_root = args.sample_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    with manifest.open(newline="", encoding="utf-8") as stream:
        samples = list(csv.DictReader(stream))
    if not samples:
        raise ValueError("Manifest contains no samples")

    completed: list[dict[str, str]] = []
    if output.exists():
        with output.open(newline="", encoding="utf-8") as stream:
            completed = list(csv.DictReader(stream))
        if len(completed) > len(samples):
            raise ValueError("Output contains more rows than the manifest")
        for expected, actual in zip(samples, completed):
            if (
                expected["sample_path"] != actual["sample_path"]
                or expected["sample_sha256"] != actual["sample_sha256"]
            ):
                raise ValueError("Existing output does not match the manifest prefix")

    config = load_runtime_config().detector
    detector = Detector(config, args.device)
    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if completed else "w"
    with output.open(mode, newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        if not completed:
            writer.writeheader()
        for start in range(len(completed), len(samples), args.batch_size):
            batch_samples = samples[start : start + args.batch_size]
            tensors = []
            for sample in batch_samples:
                image_path = sample_root / sample["sample_path"]
                if sha256(image_path) != sample["sample_sha256"]:
                    raise ValueError(f"Sample SHA-256 mismatch: {sample['sample_path']}")
                tensor, _, _ = load_image(
                    detector.cv2,
                    detector.torch,
                    detector.model.sam,
                    image_path,
                    detector.device,
                    config.preprocess_mode,
                )
                tensors.append(tensor)
            images = detector.torch.cat(tensors, dim=0)
            with detector.torch.inference_mode():
                logits = detector.model(images).flatten()
                scores = detector.torch.sigmoid(logits)
            for sample, logit, score in zip(batch_samples, logits, scores):
                score_value = float(score.item())
                writer.writerow(
                    {
                        "sample_path": sample["sample_path"],
                        "sample_sha256": sample["sample_sha256"],
                        "expected_source_class": sample["expected_source_class"],
                        "generator": sample["generator"],
                        "split": sample.get("split", ""),
                        "family_id": sample.get("family_id", ""),
                        "logit": float(logit.detach().cpu()),
                        "score_generated": score_value,
                        "prediction": (
                            "generated" if score_value > config.threshold else "original"
                        ),
                        "threshold": config.threshold,
                        "model_version": config.version,
                        "weight_sha256": config.weight_sha256,
                        "device": str(detector.device),
                    }
                )
            stream.flush()
            done = start + len(batch_samples)
            print(f"Processed {done}/{len(samples)}", flush=True)

    metadata = {
        "manifest": str(manifest),
        "manifest_sha256": sha256(manifest),
        "sample_root": str(sample_root),
        "sample_count": len(samples),
        "output": str(output),
        "output_sha256": sha256(output),
        "model_version": config.version,
        "weight_sha256": config.weight_sha256,
        "threshold": config.threshold,
        "preprocess_mode": config.preprocess_mode,
        "device": str(detector.device),
        "batch_size": args.batch_size,
    }
    metadata_path = output.with_suffix(output.suffix + ".metadata.json")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {output} and {metadata_path}")


if __name__ == "__main__":
    main()
