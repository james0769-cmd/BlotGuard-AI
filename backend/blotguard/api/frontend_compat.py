"""Frontend v0.1 compatibility routes.

These routes match the page/API draft shared by the frontend team while the
canonical backend contract remains under /api/v1.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, g, request, send_file
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from backend.blotguard.core.errors import AppError
from backend.blotguard.domain.contracts import SCORE_SEMANTICS, TaskStatus


frontend_compat = Blueprint("frontend_compat", __name__)


STATUS_MAP = {
    TaskStatus.QUEUED: "pending",
    TaskStatus.EXTRACTING: "processing",
    TaskStatus.INFERENCING: "processing",
    TaskStatus.REPORTING: "processing",
    TaskStatus.SUCCEEDED: "completed",
    TaskStatus.FAILED: "failed",
    TaskStatus.CANCELLED: "failed",
}

PROGRESS_MAP = {
    TaskStatus.QUEUED: 0,
    TaskStatus.EXTRACTING: 25,
    TaskStatus.INFERENCING: 65,
    TaskStatus.REPORTING: 90,
    TaskStatus.SUCCEEDED: 100,
    TaskStatus.FAILED: 100,
    TaskStatus.CANCELLED: 100,
}


def _task_status(value: str) -> TaskStatus:
    return TaskStatus(value)


def _frontend_status(task: dict[str, Any]) -> str:
    return STATUS_MAP[_task_status(task["status"])]


def _progress(task: dict[str, Any]) -> int:
    return PROGRESS_MAP[_task_status(task["status"])]


def _file_size(task: dict[str, Any]) -> int | None:
    path = task.get("source_path")
    if not path:
        return None
    storage = current_app.extensions["blotguard_storage"]
    try:
        return storage.absolute(path).stat().st_size
    except OSError:
        return None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _processing_time(task: dict[str, Any]) -> float | None:
    created = _parse_time(task.get("created_at"))
    completed = _parse_time(task.get("completed_at"))
    if created is None or completed is None:
        return None
    return max(0.0, round((completed - created).total_seconds(), 3))


def _first_item(task: dict[str, Any]) -> dict[str, Any] | None:
    return next((item for item in task.get("items", []) if item), None)


def _artifact_url(
    item: dict[str, Any] | None, *kinds: str
) -> str | None:
    if item is None:
        return None
    wanted = set(kinds)
    artifact = next(
        (
            current
            for current in item.get("artifacts", [])
            if current.get("kind") in wanted
        ),
        None,
    )
    return None if artifact is None else artifact["url"]


def _conclusion(task: dict[str, Any], score: float | None) -> str:
    if _frontend_status(task) == "failed":
        error = task.get("error") or {}
        return error.get("message") or "检测失败，请检查文件后重新上传。"
    if score is not None:
        return "模型已返回风险分数；五级风险阈值尚未确认，请结合原始实验数据人工复核。"
    return "任务仍在处理中，请稍后刷新检测结果。"


def _summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "file_name": task["input"]["filename"],
        "file_size": _file_size(task),
        "status": _frontend_status(task),
        "progress": _progress(task),
        "created_at": task["created_at"],
        "completed_at": task.get("completed_at"),
        "error_message": (
            (task.get("error") or {}).get("message")
            if task.get("error")
            else None
        ),
    }


def _result(task: dict[str, Any]) -> dict[str, Any]:
    item = _first_item(task)
    score = None if item is None else item.get("score_generated")
    model = task.get("model") or {}
    summary = _summary(task)
    mask_url = _artifact_url(item, "mask", "mask_overlay")
    mask_available = mask_url is not None
    return {
        **summary,
        # Keep the contract names and the current frontend service aliases
        # together until the frontend normalizes its response model.
        "filename": summary["file_name"],
        "original_image_url": _artifact_url(item, "extracted_image"),
        "mask_available": mask_available,
        "mask_image_url": mask_url,
        "localization_message": (
            None if mask_available else "当前版本不提供区域定位"
        ),
        "overall_score": score,
        "score_generated": score,
        "score_semantics": SCORE_SEMANTICS if score is not None else None,
        "prediction": None if item is None else item.get("prediction"),
        "threshold": None if item is None else item.get("threshold"),
        "overall_risk": None,
        "risk_level": None,
        "suspect_regions": [],
        "model_probabilities": [],
        "model_version": model.get("version"),
        "weight_sha256": model.get("weight_sha256"),
        "device": model.get("device"),
        "processing_time": _processing_time(task),
        "conclusion": _conclusion(task, score),
    }


def _full_task(task_id: str) -> dict[str, Any]:
    repository = current_app.extensions["blotguard_repository"]
    return repository.task_detail(task_id, include_paths=True)


@frontend_compat.post("/auth/login")
def mock_login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username") or "mock-user")
    return {
        "access_token": "mock-access-token",
        "user": {
            "id": 1,
            "username": username,
            "role": "developer",
        },
    }


@frontend_compat.post("/tasks/upload")
def upload_task():
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
        localize=False,
    )
    return _summary(_full_task(task["task_id"])), 201


@frontend_compat.get("/tasks/<task_id>")
def get_task(task_id: str):
    return _summary(_full_task(task_id))


@frontend_compat.get("/tasks/<task_id>/result")
def get_task_result(task_id: str):
    return _result(_full_task(task_id))


@frontend_compat.get("/tasks/<task_id>/report")
def get_task_report(task_id: str):
    task = _full_task(task_id)
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
    storage = current_app.extensions["blotguard_storage"]
    return send_file(
        storage.absolute(report["path"]),
        mimetype=report["media_type"],
        as_attachment=True,
        download_name=f"detection_report_{task_id}.pdf",
        conditional=True,
    )


@frontend_compat.errorhandler(AppError)
def handle_compat_app_error(error: AppError):
    return (
        {
            "error": error.code,
            "message": error.message,
            "details": error.details,
            "request_id": getattr(g, "request_id", None),
        },
        error.status_code,
    )


@frontend_compat.errorhandler(RequestEntityTooLarge)
def handle_compat_too_large(_error):
    runtime = current_app.extensions["blotguard_config"]
    return (
        {
            "error": "FILE_TOO_LARGE",
            "message": "Uploaded file exceeds the configured size limit",
            "details": {"max_bytes": runtime.max_upload_bytes},
            "request_id": getattr(g, "request_id", None),
        },
        413,
    )


@frontend_compat.errorhandler(HTTPException)
def handle_compat_http_error(error: HTTPException):
    return (
        {
            "error": error.name.upper().replace(" ", "_"),
            "message": error.description,
            "details": {},
            "request_id": getattr(g, "request_id", None),
        },
        error.code or 500,
    )
