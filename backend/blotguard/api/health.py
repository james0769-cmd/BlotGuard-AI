"""Service health endpoint."""

from . import api


@api.get("/health")
def health():
    return {"status": "ok", "service": "blotguard-api"}
