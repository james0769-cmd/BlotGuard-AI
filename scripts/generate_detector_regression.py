#!/usr/bin/env python
"""Generate deterministic Detector outputs for the fixed 25-image sample set."""

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
from backend.blotguard.inference.detector import Detector


DEFAULT_MANIFEST = (
    ROOT / "sample_data" / "western_blots_dataset" / "sample_manifest.csv"
)
DEFAULT_JSON = (
    ROOT / "sample_data" / "western_blots_dataset" / "detector_golden.json"
)
DEFAULT_CSV = (
    ROOT / "sample_data" / "western_blots_dataset" / "detector_golden.csv"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the fixed Detector golden regression outputs."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as stream:
        samples = list(csv.DictReader(stream))
    if len(samples) != 25:
        raise ValueError(f"Expected 25 samples, found {len(samples)}")

    config = load_runtime_config().detect
    detector = Detector(config, args.device)
    rows = []
    for index, sample in enumerate(samples, start=1):
        image_path = ROOT / sample["sample_path"]
        actual_sha256 = sha256(image_path)
        if actual_sha256 != sample["sample_sha256"]:
            raise ValueError(f"Sample SHA-256 mismatch: {sample['sample_path']}")

        result = detector.predict(image_path).to_dict()
        result["sample_path"] = sample["sample_path"]
        result["sample_sha256"] = actual_sha256
        result["expected_source_class"] = sample["expected_source_class"]
        result["generator"] = sample["generator"]
        rows.append(result)
        print(f"[{index:02d}/25] {sample['sample_path']}", flush=True)

    fieldnames = [
        "sample_path",
        "sample_sha256",
        "expected_source_class",
        "generator",
        "logit",
        "score_generated",
        "score_semantics",
        "prediction",
        "threshold",
        "model_name",
        "model_version",
        "weight_sha256",
        "device",
        "is_mock",
        "task",
    ]
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with args.csv_output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(
            {**row, "is_mock": str(row["is_mock"]).lower()}
            for row in rows
        )

    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.csv_output}")


if __name__ == "__main__":
    main()
