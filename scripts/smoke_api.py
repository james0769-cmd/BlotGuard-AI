#!/usr/bin/env python
"""Run a complete local API smoke test using one sample image."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_IMAGE = (
    ROOT
    / "sample_data"
    / "western_blots_dataset"
    / "real"
    / "real_img_00000.png"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the BlotGuard API")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument(
        "--mode", choices=("mock", "real"), default="mock"
    )
    parser.add_argument("--token", default=os.environ.get("BLOTGUARD_ACCESS_TOKEN"))
    args = parser.parse_args()
    if not args.token:
        parser.error("Set BLOTGUARD_ACCESS_TOKEN to a login access token")

    os.environ["BLOTGUARD_INFERENCE_MODE"] = args.mode
    os.environ["BLOTGUARD_EXECUTION_MODE"] = "inline"

    from backend.blotguard import create_app

    app = create_app({"TESTING": True})
    try:
        with args.image.open("rb") as stream:
            response = app.test_client().post(
                "/api/v1/analyses",
                data={"file": (stream, args.image.name)},
                content_type="multipart/form-data",
                headers={"Authorization": f"Bearer {args.token}"},
            )
        print(json.dumps(response.get_json(), ensure_ascii=False, indent=2))
        return 0 if response.status_code == 202 else 1
    finally:
        app.extensions["blotguard_analysis_service"].executor.shutdown(wait=True)


if __name__ == "__main__":
    raise SystemExit(main())
