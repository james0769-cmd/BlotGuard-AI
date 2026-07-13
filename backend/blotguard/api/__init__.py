"""HTTP routes exposed by the BlotGuard API."""

from flask import Blueprint


api = Blueprint("api", __name__)

from . import health as health  # noqa: E402,F401
from . import detect as detect  # noqa: E402,F401
