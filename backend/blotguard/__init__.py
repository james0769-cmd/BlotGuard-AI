"""Flask application factory for the BlotGuard API."""

from __future__ import annotations

import logging
from typing import Any, Mapping
from uuid import uuid4

from flask import Flask, g, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .core.config import RuntimeConfig, load_runtime_config
from .core.errors import AppError
from .inference.provider import InferenceProvider
from .persistence.repository import AnalysisRepository
from .services.analysis import AnalysisService
from .services.extraction import ExtractionService
from .services.reporting import ReportService
from .services.storage import LocalStorage


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    overrides = dict(test_config or {})
    runtime = overrides.pop("RUNTIME_CONFIG", None)
    if runtime is None:
        runtime = load_runtime_config()

    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=runtime.max_upload_bytes,
        JSON_SORT_KEYS=False,
    )
    app.config.from_mapping(overrides)
    CORS(
        app,
        resources={r"/api/*": {"origins": list(runtime.allowed_origins)}},
    )

    repository = AnalysisRepository(runtime.database_url)
    repository.init_schema()
    storage = LocalStorage(runtime.storage_root, runtime.max_upload_bytes)
    inference = InferenceProvider(runtime)
    extractor = ExtractionService(runtime, storage)
    reports = ReportService(runtime, storage)
    analysis = AnalysisService(
        runtime,
        repository,
        storage,
        extractor,
        inference,
        reports,
    )

    app.extensions["blotguard_config"] = runtime
    app.extensions["blotguard_repository"] = repository
    app.extensions["blotguard_storage"] = storage
    app.extensions["blotguard_inference"] = inference
    app.extensions["blotguard_analysis_service"] = analysis

    from .api import api

    app.register_blueprint(api, url_prefix="/api/v1")
    from .api.frontend_compat import frontend_compat

    app.register_blueprint(frontend_compat, url_prefix="/api")
    _register_request_hooks(app)
    _register_error_handlers(app)
    return app


def _register_request_hooks(app: Flask) -> None:
    @app.before_request
    def set_request_id() -> None:
        supplied = request.headers.get("X-Request-ID", "").strip()
        g.request_id = supplied[:128] if supplied else str(uuid4())

    @app.after_request
    def add_response_headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response


def _register_error_handlers(app: Flask) -> None:
    def error_payload(
        code: str, message: str, details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": getattr(g, "request_id", None),
            }
        }

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return (
            error_payload(error.code, error.message, error.details),
            error.status_code,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        runtime = app.extensions["blotguard_config"]
        return (
            error_payload(
                "FILE_TOO_LARGE",
                "Uploaded file exceeds the configured size limit",
                {"max_bytes": runtime.max_upload_bytes},
            ),
            413,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return (
            error_payload(
                error.name.upper().replace(" ", "_"),
                error.description,
            ),
            error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logging.exception("Unhandled request error", exc_info=error)
        return (
            error_payload(
                "INTERNAL_ERROR",
                "An unexpected server error occurred",
            ),
            500,
        )
