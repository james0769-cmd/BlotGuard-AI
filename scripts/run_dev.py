#!/usr/bin/env python
"""Start the local development API."""

from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard import create_app


if __name__ == "__main__":
    create_app().run(
        host=os.environ.get("BLOTGUARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("BLOTGUARD_PORT", "5000")),
        debug=True,
        use_reloader=False,
    )
