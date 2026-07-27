"""Liveness and readiness endpoints."""

from flask import current_app

from . import api


@api.get("/health")
@api.get("/health/live")
def live():
    return {"status": "ok", "service": "blotguard-api"}


@api.get("/health/ready")
def ready():
    repository = current_app.extensions["blotguard_repository"]
    inference = current_app.extensions["blotguard_inference"]
    database_ready = repository.ping()
    model_ready, model_messages = inference.readiness()
    is_ready = database_ready and model_ready
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "service": "blotguard-api",
        "components": {
            "database": {
                "status": "ready" if database_ready else "not_ready"
            },
            "detector": {
                "status": "ready" if model_ready else "not_ready",
                "messages": model_messages,
            },
        },
    }
    return payload, 200 if is_ready else 503
