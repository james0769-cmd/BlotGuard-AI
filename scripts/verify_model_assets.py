#!/usr/bin/env python
"""Verify configured model assets and their tracked SHA-256 values."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard.core.config import load_runtime_config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    config = load_runtime_config()
    failed = False
    for name, model in (
        ("detector", config.detector),
        ("localizer", config.localizer),
    ):
        if not model.enabled:
            print(f"SKIP {name}: disabled")
            continue
        for label, path in (
            ("code", model.code_dir),
            ("sam", model.sam_checkpoint),
            ("lora", model.lora_weight),
        ):
            if not path.exists():
                print(f"MISSING {name}.{label}: {path}")
                failed = True
                continue
            if label == "lora":
                actual = sha256(path)
                if actual != model.weight_sha256:
                    print(
                        f"INVALID {name}.{label}: sha256 {actual}, "
                        f"expected {model.weight_sha256}"
                    )
                    failed = True
                    continue
            print(f"OK {name}.{label}: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
