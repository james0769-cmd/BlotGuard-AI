"""Flask application factory for the BlotGuard API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def create_app(test_config: Mapping[str, Any] | None = None):
    """Create and configure the Flask application."""
    from flask import Flask

    app = Flask(__name__)
    if test_config is not None:
        app.config.from_mapping(test_config)

    from .api import api

    app.register_blueprint(api, url_prefix="/api/v1")
    return app
