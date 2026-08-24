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
from backend.blotguard.domain.risk import (
    RISK_LEVEL_LABELS,
    RISK_LEVEL_SEMANTICS,
    RISK_LEVEL_VERSION,
)


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


def _report_available(task: dict[str, Any]) -> bool:
    return any(
        artifact.get("kind") == "report"
        for artifact in task.get("artifacts", [])
    )


def _conclusion(
    task: dict[str, Any], score: float | None, risk_level: str | None
) -> str:
    if _frontend_status(task) == "failed":
        error = task.get("error") or {}
        return error.get("message") or "检测失败，请检查文件后重新上传。"
    if (task.get("summary") or {}).get("not_applicable") and score is None:
        return (
            "该文件未通过 Western Blot 图像域预检，系统未执行真伪分析，"
            "也未生成真假风险分数。"
        )
    if score is not None:
        return (
            f"实验性五级风险为 {RISK_LEVEL_LABELS[risk_level]}；当前模型对 "
            "DDPM/Pix2Pix 的区分能力"
            "仍待改进，请结合原始实验数据人工复核。"
        )
    return "任务仍在处理中，请稍后刷新检测结果。"


def _summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "file_name": task["input"]["filename"],
        "file_type": task["input"].get("extension"),
        "file_size": _file_size(task),
        "status": _frontend_status(task),
        "backend_status": task["status"],
        "progress": _progress(task),
        "created_at": task["created_at"],
        "completed_at": task.get("completed_at"),
        "error_message": (
            (task.get("error") or {}).get("message")
            if task.get("error")
            else None
        ),
    }


def _item_result(item: dict[str, Any]) -> dict[str, Any]:
    mask_url = _artifact_url(item, "mask", "mask_overlay")
    risk_level = item.get("risk_level")
    return {
        "item_id": item["id"],
        "status": item["status"],
        "source_name": item["source_name"],
        "source_index": item["source_index"],
        "page_number": item.get("page_number"),
        "width": item["width"],
        "height": item["height"],
        "sha256": item["sha256"],
        "prediction": item.get("prediction"),
        "applicable": item.get("applicable", True),
        "domain_label": item.get("domain_label"),
        "domain_message": item.get("domain_message"),
        "score_generated": item.get("score_generated"),
        "score_semantics": item.get("score_semantics"),
        "threshold": item.get("threshold"),
        "risk_level": risk_level,
        "risk_level_label": (
            RISK_LEVEL_LABELS.get(risk_level) if risk_level else None
        ),
        "risk_level_semantics": item.get("risk_level_semantics"),
        "risk_level_version": item.get("risk_level_version"),
        "risk_level_is_experimental": item.get(
            "risk_level_is_experimental", True
        ),
        "original_image_url": _artifact_url(item, "extracted_image"),
        "mask_available": mask_url is not None,
        "mask_image_url": mask_url,
        "mask_coverage": item.get("mask_coverage"),
        "localization_message": (
            None if mask_url else "当前版本不提供区域定位"
        ),
        "error": item.get("error"),
    }


def _result(task: dict[str, Any]) -> dict[str, Any]:
    first_item = _first_item(task)
    items = [_item_result(item) for item in task.get("items", [])]
    result_summary = task.get("summary") or {}
    score = result_summary.get("score_generated")
    risk_level = result_summary.get("risk_level")
    model = task.get("model") or {}
    summary = _summary(task)
    mask_url = _artifact_url(first_item, "mask", "mask_overlay")
    mask_available = any(item["mask_available"] for item in items)
    report_available = _report_available(task)
    return {
        **summary,
        # Keep the contract names and the current frontend service aliases
        # together until the frontend normalizes its response model.
        "filename": summary["file_name"],
        "original_image_url": _artifact_url(first_item, "extracted_image"),
        "image_count": len(items),
        "items": items,
        "result_summary": result_summary,
        "mask_available": mask_available,
        "mask_image_url": mask_url,
        "localization_message": (
            None if mask_available else "当前版本不提供区域定位"
        ),
        "overall_score": score,
        "score_generated": score,
        "score_semantics": SCORE_SEMANTICS if score is not None else None,
        "prediction": result_summary.get("prediction"),
        "applicable": score is not None,
        "domain_label": (
            "western_blot" if score is not None else "non_western_blot"
        ),
        "domain_message": (
            first_item.get("domain_message") if first_item else None
        ),
        "threshold": model.get("threshold"),
        "overall_risk": risk_level,
        "risk_level": risk_level,
        "risk_level_label": (
            RISK_LEVEL_LABELS.get(risk_level) if risk_level else None
        ),
        "risk_level_semantics": RISK_LEVEL_SEMANTICS,
        "risk_level_version": RISK_LEVEL_VERSION,
        "risk_level_is_experimental": True,
        "suspect_regions": [],
        "model_probabilities": [],
        "model_version": model.get("version"),
        "weight_sha256": model.get("weight_sha256"),
        "device": model.get("device"),
        "is_mock": bool(model.get("is_mock", False)),
        "report_available": report_available,
        "report_url": (
            f'/api/tasks/{task["task_id"]}/report'
            if report_available
            else None
        ),
        "processing_time": _processing_time(task),
        "conclusion": _conclusion(task, score, risk_level),
    }


def _full_task(task_id: str) -> dict[str, Any]:
    repository = current_app.extensions["blotguard_repository"]
    return repository.task_detail(task_id, include_paths=True)


def _credentials() -> tuple[str, str]:
    body = request.get_json(silent=True) or {}
    return str(body.get("username") or ""), str(body.get("password") or "")


def _bearer_token() -> str:
    authorization = request.headers.get("Authorization", "").strip()
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise AppError(
            "AUTHENTICATION_REQUIRED",
            "A Bearer access token is required",
            401,
        )
    return token.strip()


@frontend_compat.post("/auth/register")
def register():
    username, password = _credentials()
    auth = current_app.extensions["blotguard_auth_service"]
    return auth.register(username, password), 201


@frontend_compat.post("/auth/login")
def login():
    username, password = _credentials()
    auth = current_app.extensions["blotguard_auth_service"]
    return auth.login(username, password)


@frontend_compat.get("/auth/me")
def current_user():
    auth = current_app.extensions["blotguard_auth_service"]
    return {"user": auth.authenticate(_bearer_token())}


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


@frontend_compat.get("/tasks")
def list_tasks():
    limit = request.args.get("limit", default=200, type=int)
    if limit is None or limit <= 0 or limit > 500:
        raise AppError("INVALID_LIMIT", "limit must be between 1 and 500", 400)
    service = current_app.extensions["blotguard_analysis_service"]
    return {"tasks": [_summary(task) for task in service.list(limit=limit)]}


@frontend_compat.get("/tasks/<task_id>")
def get_task(task_id: str):
    return _summary(_full_task(task_id))


@frontend_compat.delete("/tasks/<task_id>")
def delete_task(task_id: str):
    service = current_app.extensions["blotguard_analysis_service"]
    service.delete(task_id)
    return "", 204


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
        if task["status"] == TaskStatus.FAILED:
            task_error = task.get("error") or {}
            raise AppError(
                "TASK_FAILED",
                task_error.get("message") or "Analysis task failed",
                409,
                {"task_error": task_error},
            )
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
