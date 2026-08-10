#!/usr/bin/env python
"""Build a deterministic, stratified audit manifest from a labeled dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


GROUPS = (
    ("real", "original", ""),
    ("synth/stylegan2ada", "generated", "stylegan2ada"),
    ("synth/cyclegan", "generated", "cyclegan"),
    ("synth/pix2pix", "generated", "pix2pix"),
    ("synth/ddpm", "generated", "ddpm"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evenly_spaced(paths: list[Path], count: int) -> list[Path]:
    if len(paths) < count:
        raise ValueError(f"Requested {count} samples from only {len(paths)} files")
    return [paths[((2 * index + 1) * len(paths)) // (2 * count)] for index in range(count)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples-per-group", type=int, default=100)
    args = parser.parse_args()

    dataset_root = args.dataset_root.expanduser().resolve()
    rows: list[dict[str, str]] = []
    for relative_dir, expected_class, generator in GROUPS:
        directory = dataset_root / relative_dir
        paths = sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
        )
        for path in evenly_spaced(paths, args.samples_per_group):
            rows.append(
                {
                    "sample_path": path.relative_to(dataset_root).as_posix(),
                    "expected_source_class": expected_class,
                    "generator": generator,
                    "sample_sha256": sha256(path),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "sample_path",
                "expected_source_class",
                "generator",
                "sample_sha256",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} samples to {args.output}")


if __name__ == "__main__":
    main()
