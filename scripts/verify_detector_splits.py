#!/usr/bin/env python
"""Verify frozen detector split manifests against the source dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from build_detector_splits import BKTree, IMAGE_SUFFIXES, sha256


SPLITS = ("calibration", "test", "reserve", "excluded")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--split-dir", type=Path, required=True)
    args = parser.parse_args()

    dataset_root = args.dataset_root.expanduser().resolve()
    split_dir = args.split_dir.expanduser().resolve()
    metadata = json.loads(
        (split_dir / "detector_split_metadata.json").read_text(encoding="utf-8")
    )

    rows_by_split: dict[str, list[dict[str, str]]] = {}
    seen_paths: set[str] = set()
    seen_families: dict[str, str] = {}
    seen_hashes: dict[str, str] = {}
    for split in SPLITS:
        manifest = split_dir / f"detector_{split}_manifest.csv"
        expected_manifest_hash = metadata["manifest_sha256"][split]
        if sha256(manifest) != expected_manifest_hash:
            raise ValueError(f"Manifest SHA-256 mismatch: {manifest}")
        rows = read_rows(manifest)
        rows_by_split[split] = rows
        for row in rows:
            if row["split"] != split:
                raise ValueError(f"Wrong split value for {row['sample_path']}")
            if row["sample_path"] in seen_paths:
                raise ValueError(f"Path appears in multiple manifests: {row['sample_path']}")
            seen_paths.add(row["sample_path"])
            previous_family_split = seen_families.setdefault(row["family_id"], split)
            if previous_family_split != split:
                raise ValueError(f"Family crosses splits: {row['family_id']}")
            if split != "excluded":
                previous_hash_split = seen_hashes.get(row["sample_sha256"])
                if previous_hash_split is not None and (
                    previous_hash_split != split
                    or split in {"calibration", "test"}
                ):
                    raise ValueError(
                        f"Exact image content is duplicated in frozen splits: "
                        f"{row['sample_sha256']}"
                    )
                seen_hashes.setdefault(row["sample_sha256"], split)
            image_path = dataset_root / row["sample_path"]
            if sha256(image_path) != row["sample_sha256"]:
                raise ValueError(f"Image SHA-256 mismatch: {row['sample_path']}")

    dataset_paths = {
        path.relative_to(dataset_root).as_posix()
        for path in dataset_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }
    if seen_paths != dataset_paths:
        raise ValueError(
            f"Dataset coverage mismatch: missing={len(dataset_paths - seen_paths)}, "
            f"extra={len(seen_paths - dataset_paths)}"
        )

    maximum_distance = int(metadata["phash_max_hamming_distance"])
    calibration_tree = BKTree()
    for row in rows_by_split["calibration"]:
        calibration_tree.add(int(row["phash64"], 16))
    for row in rows_by_split["test"]:
        if calibration_tree.has_within(int(row["phash64"], 16), maximum_distance):
            raise ValueError(f"Calibration/test near duplicate: {row['sample_path']}")

    frozen_tree = BKTree()
    for split in ("calibration", "test"):
        for row in rows_by_split[split]:
            frozen_tree.add(int(row["phash64"], 16))
    for row in rows_by_split["reserve"]:
        if frozen_tree.has_within(int(row["phash64"], 16), maximum_distance):
            raise ValueError(f"Frozen/reserve near duplicate: {row['sample_path']}")

    for split in ("calibration", "test", "reserve"):
        actual_counts = Counter(row["generator"] or "real" for row in rows_by_split[split])
        if dict(actual_counts) != metadata["split_counts"][split]:
            raise ValueError(f"Group count mismatch for {split}")

    print(
        json.dumps(
            {
                "status": "ok",
                "dataset_files": len(dataset_paths),
                "split_rows": {
                    split: len(rows) for split, rows in rows_by_split.items()
                },
                "unique_families": len(seen_families),
                "unique_content_hashes": len(seen_hashes),
                "phash_max_hamming_distance": maximum_distance,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
