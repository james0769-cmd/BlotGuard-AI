"""Analysis task creation, lookup, report download, and deletion."""

from __future__ import annotations

from flask import current_app, request, send_file

from backend.blotguard.core.errors import AppError
from . import api


def _boolean_form(name: str, default: bool = False) -> bool:
    value = request.form.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise AppError(
        "INVALID_BOOLEAN",
        f"Form field '{name}' must be true or false",
        400,
    )


@api.post("/analyses")
def create_analysis():
    uploaded = request.files.get("file")
    if uploaded is None:
        raise AppError(
            "MISSING_FILE",
            "Multipart form field 'file' is required",
            400,
        )
    if not uploaded.filename:
        raise AppError("MISSING_FILENAME", "Uploaded file has no filename", 400)
    service = current_app.extensions["blotguard_analysis_service"]
    task = service.submit(
        filename=uploaded.filename,
        media_type=uploaded.mimetype,
        stream=uploaded.stream,
        localize=_boolean_form("localize"),
    )
    return task, 202


@api.get("/analyses/<task_id>")
def get_analysis(task_id: str):
    service = current_app.extensions["blotguard_analysis_service"]
    return service.get(task_id)


@api.get("/analyses/<task_id>/report")
def get_report(task_id: str):
    repository = current_app.extensions["blotguard_repository"]
    storage = current_app.extensions["blotguard_storage"]
    task = repository.task_detail(task_id, include_paths=True)
    report = next(
        (
            artifact
            for artifact in task["artifacts"]
            if artifact["kind"] == "report"
        ),
        None,
    )
    if report is None:
        raise AppError(
            "REPORT_NOT_READY",
            "The report is not available for this task",
            409,
        )
    return send_file(
        storage.absolute(report["path"]),
        mimetype=report["media_type"],
        as_attachment=True,
        download_name=report["filename"],
        conditional=True,
    )


@api.delete("/analyses/<task_id>")
def delete_analysis(task_id: str):
    service = current_app.extensions["blotguard_analysis_service"]
    service.delete(task_id)
    return "", 204
