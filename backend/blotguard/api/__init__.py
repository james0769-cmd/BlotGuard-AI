"""Versioned HTTP API blueprint."""

from flask import Blueprint


api = Blueprint("api", __name__)

from . import analyses as analyses  # noqa: E402,F401
from . import artifacts as artifacts  # noqa: E402,F401
from . import detect as detect  # noqa: E402,F401
from . import health as health  # noqa: E402,F401
