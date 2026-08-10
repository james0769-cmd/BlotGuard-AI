#!/usr/bin/env python
"""Build frozen detector calibration, test, reserve, and exclusion manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import re


GROUPS = (
    ("real", "original", ""),
    ("synth/stylegan2ada", "generated", "stylegan2ada"),
    ("synth/cyclegan", "generated", "cyclegan"),
    ("synth/pix2pix", "generated", "pix2pix"),
    ("synth/ddpm", "generated", "ddpm"),
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
FAMILY_PATTERN = re.compile(r"(\d+)$")
MANIFEST_FIELDS = (
    "sample_path",
    "sample_sha256",
    "expected_source_class",
    "generator",
    "split",
    "family_id",
    "phash64",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def family_id(path: Path) -> str:
    match = FAMILY_PATTERN.search(path.stem)
    if match is None:
        raise ValueError(f"Cannot derive family id from {path.name}")
    return f"western-blot-{int(match.group(1)):05d}"


def phash64(path: Path) -> int:
    import cv2
    import numpy as np

    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Cannot read image: {path}")
    resized = cv2.resize(image, (32, 32), interpolation=cv2.INTER_AREA)
    transformed = cv2.dct(np.float32(resized))[:8, :8]
    median = float(np.median(transformed.flatten()[1:]))
    bits = transformed > median
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


class BKTree:
    def __init__(self):
        self.root: tuple[int, dict[int, object]] | None = None

    def add(self, value: int) -> None:
        if self.root is None:
            self.root = (value, {})
            return
        node = self.root
        while True:
            current, children = node
            distance = (value ^ current).bit_count()
            child = children.get(distance)
            if child is None:
                children[distance] = (value, {})
                return
            node = child  # type: ignore[assignment]

    def has_within(self, value: int, maximum_distance: int) -> bool:
        if self.root is None:
            return False
        pending = [self.root]
        while pending:
            current, children = pending.pop()
            distance = (value ^ current).bit_count()
            if distance <= maximum_distance:
                return True
            lower = distance - maximum_distance
            upper = distance + maximum_distance
            pending.extend(
                child
                for edge, child in children.items()
                if lower <= edge <= upper
            )
        return False


def parse_exclude_manifest(value: str) -> tuple[Path, Path]:
    try:
        raw_manifest, raw_root = value.split("|", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "exclude manifest must be MANIFEST|SAMPLE_ROOT"
        ) from exc
    return Path(raw_manifest).expanduser().resolve(), Path(raw_root).expanduser().resolve()


def read_manifest_paths(manifest: Path, sample_root: Path) -> list[Path]:
    with manifest.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return [(sample_root / row["sample_path"]).resolve() for row in rows]


def historical_paths(face_split_root: Path) -> list[Path]:
    paths: set[Path] = set()
    for manifest in face_split_root.glob("*.txt"):
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            relative = line.split(",", 1)[0]
            path = (face_split_root / relative).resolve()
            if path.is_file():
                paths.add(path)
    historical_dir = face_split_root / "blots_20"
    if historical_dir.is_dir():
        paths.update(
            path.resolve()
            for path in historical_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    return sorted(paths)


def write_manifest(path: Path, rows: list[dict[str, str]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return sha256(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--face-split-root", type=Path, required=True)
    parser.add_argument(
        "--exclude-manifest", action="append", type=parse_exclude_manifest, default=[]
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--calibration-per-group", type=int, default=500)
    parser.add_argument("--test-per-group", type=int, default=1000)
    parser.add_argument("--seed", default="blotguard-detector-split-v1")
    parser.add_argument("--phash-distance", type=int, default=4)
    args = parser.parse_args()

    dataset_root = args.dataset_root.expanduser().resolve()
    face_split_root = args.face_split_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    by_sha256: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for relative_dir, expected_class, generator in GROUPS:
        directory = dataset_root / relative_dir
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            digest = sha256(path)
            row: dict[str, object] = {
                "path": path,
                "sample_path": path.relative_to(dataset_root).as_posix(),
                "sample_sha256": digest,
                "expected_source_class": expected_class,
                "generator": generator,
                "family_id": family_id(path),
            }
            rows.append(row)
            by_sha256[digest].append(row)
            by_family[str(row["family_id"])].append(row)

    excluded_reasons: dict[str, set[str]] = defaultdict(set)
    historical = historical_paths(face_split_root)
    historical_hashes = {sha256(path) for path in historical}
    historical_phashes = BKTree()
    for path in historical:
        if path.name.startswith(("real_img_", "stylegan2ada_", "cyclegan_", "pix2pix_", "ddpm_")):
            historical_phashes.add(phash64(path))
    for digest in historical_hashes:
        for row in by_sha256.get(digest, []):
            excluded_reasons[str(row["family_id"])].add("historical_train_or_val")

    for manifest, sample_root in args.exclude_manifest:
        reason = f"previously_evaluated:{manifest.name}"
        for path in read_manifest_paths(manifest, sample_root):
            if not path.is_file():
                raise FileNotFoundError(path)
            digest = sha256(path)
            matches = by_sha256.get(digest, [])
            for row in matches:
                excluded_reasons[str(row["family_id"])].add(reason)

    for index, row in enumerate(rows, start=1):
        row["phash"] = phash64(Path(row["path"]))
        if historical_phashes.has_within(int(row["phash"]), args.phash_distance):
            excluded_reasons[str(row["family_id"])].add("near_historical_train_or_val")
        if index % 2000 == 0:
            print(f"Hashed {index}/{len(rows)} images", flush=True)

    required_groups = len(GROUPS)
    eligible_families = [
        current
        for current, members in by_family.items()
        if len(members) == required_groups and current not in excluded_reasons
    ]
    eligible_families.sort(
        key=lambda current: hashlib.sha256(
            f"{args.seed}:{current}".encode("utf-8")
        ).hexdigest()
    )
    for current in eligible_families:
        digests = [str(row["sample_sha256"]) for row in by_family[current]]
        if len(set(digests)) != len(digests):
            excluded_reasons[current].add("exact_duplicate_within_family")

    frozen_hashes: set[str] = set()
    calibration_families: set[str] = set()
    for current in eligible_families:
        if current in excluded_reasons:
            continue
        digests = {str(row["sample_sha256"]) for row in by_family[current]}
        if digests & frozen_hashes:
            excluded_reasons[current].add("exact_duplicate_within_calibration")
            continue
        calibration_families.add(current)
        frozen_hashes.update(digests)
        if len(calibration_families) == args.calibration_per_group:
            break
    if len(calibration_families) != args.calibration_per_group:
        raise ValueError(
            f"Could select only {len(calibration_families)} calibration families"
        )

    calibration_tree = BKTree()
    for current in calibration_families:
        for row in by_family[current]:
            calibration_tree.add(int(row["phash"]))

    test_families: set[str] = set()
    for current in eligible_families:
        if current in calibration_families or current in excluded_reasons:
            continue
        digests = {str(row["sample_sha256"]) for row in by_family[current]}
        if digests & frozen_hashes:
            excluded_reasons[current].add("exact_duplicate_with_frozen_split")
            continue
        if any(
            calibration_tree.has_within(int(row["phash"]), args.phash_distance)
            for row in by_family[current]
        ):
            excluded_reasons[current].add("near_calibration")
            continue
        test_families.add(current)
        frozen_hashes.update(digests)
        if len(test_families) == args.test_per_group:
            break
    if len(test_families) != args.test_per_group:
        raise ValueError(f"Could select only {len(test_families)} test families")

    frozen_tree = BKTree()
    for current in calibration_families | test_families:
        for row in by_family[current]:
            frozen_tree.add(int(row["phash"]))

    reserve_families: set[str] = set()
    for current, members in by_family.items():
        if current in calibration_families or current in test_families:
            continue
        if current in excluded_reasons:
            continue
        if any(str(row["sample_sha256"]) in frozen_hashes for row in members):
            excluded_reasons[current].add("exact_duplicate_with_frozen_split")
            continue
        if any(
            frozen_tree.has_within(int(row["phash"]), args.phash_distance)
            for row in members
        ):
            excluded_reasons[current].add("near_frozen_calibration_or_test")
            continue
        reserve_families.add(current)

    split_families = {
        "calibration": calibration_families,
        "test": test_families,
        "reserve": reserve_families,
    }
    manifest_hashes: dict[str, str] = {}
    split_counts: dict[str, dict[str, int]] = {}
    for split, families in split_families.items():
        manifest_rows = []
        for row in rows:
            if row["family_id"] not in families:
                continue
            manifest_rows.append(
                {
                    field: (
                        split
                        if field == "split"
                        else f"{int(row['phash']):016x}"
                        if field == "phash64"
                        else str(row[field])
                    )
                    for field in MANIFEST_FIELDS
                }
            )
        manifest_rows.sort(key=lambda row: (row["generator"], row["sample_path"]))
        manifest_path = output_dir / f"detector_{split}_manifest.csv"
        manifest_hashes[split] = write_manifest(manifest_path, manifest_rows)
        split_counts[split] = dict(Counter(row["generator"] or "real" for row in manifest_rows))

    exclusion_rows = []
    for row in rows:
        reasons = excluded_reasons.get(str(row["family_id"]))
        if not reasons:
            continue
        exclusion_rows.append(
            {
                "sample_path": str(row["sample_path"]),
                "sample_sha256": str(row["sample_sha256"]),
                "expected_source_class": str(row["expected_source_class"]),
                "generator": str(row["generator"]),
                "split": "excluded",
                "family_id": str(row["family_id"]),
                "phash64": f"{int(row['phash']):016x}",
            }
        )
    exclusion_rows.sort(key=lambda row: (row["generator"], row["sample_path"]))
    manifest_hashes["excluded"] = write_manifest(
        output_dir / "detector_excluded_manifest.csv", exclusion_rows
    )

    reason_counts = Counter(
        reason for reasons in excluded_reasons.values() for reason in reasons
    )
    metadata = {
        "schema_version": 1,
        "dataset_root_layout": "western_blots_dataset/{real,synth/<generator>}",
        "dataset_file_count": len(rows),
        "seed": args.seed,
        "family_rule": "shared trailing numeric image id across all five groups",
        "phash_algorithm": "32x32 grayscale DCT, top-left 8x8 median hash",
        "phash_max_hamming_distance": args.phash_distance,
        "calibration_per_group": args.calibration_per_group,
        "test_per_group": args.test_per_group,
        "split_counts": split_counts,
        "excluded_family_reason_counts": dict(sorted(reason_counts.items())),
        "source_split_manifests": {
            path.name: sha256(path) for path in sorted(face_split_root.glob("*.txt"))
        },
        "previously_evaluated_manifests": {
            str(path): sha256(path) for path, _ in args.exclude_manifest
        },
        "manifest_sha256": manifest_hashes,
        "usage": {
            "calibration": "threshold and score calibration only",
            "test": "one-time final evaluation after model and thresholds are frozen",
            "reserve": "future development; never train the current frozen model on test",
            "excluded": "historical, previously evaluated, or perceptually conflicting samples",
        },
    }
    metadata_path = output_dir / "detector_split_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote detector splits to {output_dir}")


if __name__ == "__main__":
    main()
