#!/usr/bin/env python3
"""Delete terminal analysis tasks older than the configured retention period."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard import create_app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=None,
        help="Override app.task_retention_days from the runtime config",
    )
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    app = create_app()
    service = app.extensions["blotguard_analysis_service"]
    try:
        result = service.cleanup_expired(
            older_than_days=args.older_than_days,
            limit=args.limit,
        )
    finally:
        service.executor.shutdown(wait=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
