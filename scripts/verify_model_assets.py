#!/usr/bin/env python
"""Verify local model weights against the tracked artifact manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "models" / "manifest.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify BlotGuard model weights.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--weights-root", type=Path, default=None)
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    with manifest_path.open("r", encoding="utf-8") as stream:
        manifest = yaml.safe_load(stream)

    weights_root = args.weights_root
    if weights_root is None:
        weights_root = ROOT / manifest["weights_root"]
    weights_root = weights_root.expanduser().resolve()

    failed = False
    for name, expected in manifest["artifacts"].items():
        path = weights_root / expected["path"]
        if not path.is_file():
            print(f"MISSING {name}: {path}")
            failed = True
            continue

        actual_size = path.stat().st_size
        actual_sha256 = sha256(path)
        if actual_size != expected["size_bytes"]:
            print(
                f"INVALID {name}: size {actual_size}, "
                f"expected {expected['size_bytes']}"
            )
            failed = True
            continue
        if actual_sha256 != expected["sha256"]:
            print(f"INVALID {name}: sha256 {actual_sha256}")
            failed = True
            continue

        print(f"OK {name}: {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
