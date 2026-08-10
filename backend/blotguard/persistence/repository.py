"""Database operations and public task serialization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from backend.blotguard.domain.contracts import (
    DetectionResult,
    ExtractedImage,
    ItemStatus,
    ModelMetadata,
    SCORE_SEMANTICS,
    TaskStatus,
    device_from_runtime,
)
from backend.blotguard.domain.risk import (
    RISK_LEVEL_SEMANTICS,
    RISK_LEVEL_VERSION,
    risk_level_for_score,
)
from backend.blotguard.core.errors import NotFoundError
from .models import AnalysisItem, AnalysisTask, Artifact, Base


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class AnalysisRepository:
    def __init__(self, database_url: str):
        connect_args = (
            {"check_same_thread": False}
            if database_url.startswith("sqlite:")
            else {}
        )
        self.engine = create_engine(
            database_url, pool_pre_ping=True, connect_args=connect_args
        )
        self.sessions = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=Session
        )

    def init_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def ping(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
            return True
        except Exception:
            return False

    def create_task(
        self,
        task_id: str,
        original_filename: str,
        extension: str,
        media_type: str,
        source_sha256: str,
        source_path: str,
        localize_requested: bool,
    ) -> None:
        with self.sessions.begin() as session:
            session.add(
                AnalysisTask(
                    id=task_id,
                    status=TaskStatus.QUEUED,
                    original_filename=original_filename,
                    extension=extension,
                    media_type=media_type,
                    source_sha256=source_sha256,
                    source_path=source_path,
                    localize_requested=localize_requested,
                )
            )

    def set_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.sessions.begin() as session:
            task = session.get(AnalysisTask, task_id)
            if task is None:
                raise NotFoundError("analysis task", task_id)
            task.status = status
            task.error_code = error_code
            task.error_message = error_message
            if status in {
                TaskStatus.SUCCEEDED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                task.completed_at = datetime.now(timezone.utc)

    def create_items(
        self, task_id: str, images: list[ExtractedImage]
    ) -> list[str]:
        ids: list[str] = []
        with self.sessions.begin() as session:
            if session.get(AnalysisTask, task_id) is None:
                raise NotFoundError("analysis task", task_id)
            for image in images:
                item_id = str(uuid4())
                ids.append(item_id)
                session.add(
                    AnalysisItem(
                        id=item_id,
                        task_id=task_id,
                        status=ItemStatus.PENDING,
                        source_name=image.source_name,
                        source_index=image.source_index,
                        page_number=image.page_number,
                        image_path=image.path,
                        image_sha256=image.sha256,
                        width=image.width,
                        height=image.height,
                    )
                )
        return ids

    def record_detection(
        self,
        task_id: str,
        item_id: str,
        result: DetectionResult,
    ) -> None:
        with self.sessions.begin() as session:
            task = session.get(AnalysisTask, task_id)
            item = session.get(AnalysisItem, item_id)
            if task is None or item is None or item.task_id != task_id:
                raise NotFoundError("analysis item", item_id)
            item.status = ItemStatus.SUCCEEDED
            item.prediction = result.prediction
            item.score_generated = result.score_generated
            item.threshold = result.threshold
            self._set_model(task, result.model)

    def record_item_failure(
        self, item_id: str, code: str, message: str
    ) -> None:
        with self.sessions.begin() as session:
            item = session.get(AnalysisItem, item_id)
            if item is None:
                raise NotFoundError("analysis item", item_id)
            item.status = ItemStatus.FAILED
            item.error_code = code
            item.error_message = message

    @staticmethod
    def _set_model(task: AnalysisTask, model: ModelMetadata) -> None:
        task.model_name = model.name
        task.model_version = model.version
        task.model_weight_sha256 = model.weight_sha256
        task.model_threshold = model.threshold
        task.model_runtime = model.runtime
        task.model_is_mock = model.is_mock

    def create_artifact(
        self,
        task_id: str,
        *,
        kind: str,
        path: str,
        media_type: str,
        filename: str,
        item_id: str | None = None,
    ) -> str:
        artifact_id = str(uuid4())
        with self.sessions.begin() as session:
            session.add(
                Artifact(
                    id=artifact_id,
                    task_id=task_id,
                    item_id=item_id,
                    kind=kind,
                    path=path,
                    media_type=media_type,
                    filename=filename,
                )
            )
        return artifact_id

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            artifact = session.get(Artifact, artifact_id)
            if artifact is None:
                raise NotFoundError("artifact", artifact_id)
            return {
                "id": artifact.id,
                "task_id": artifact.task_id,
                "kind": artifact.kind,
                "path": artifact.path,
                "media_type": artifact.media_type,
                "filename": artifact.filename,
            }

    def task_detail(
        self, task_id: str, *, include_paths: bool = False
    ) -> dict[str, Any]:
        statement = (
            select(AnalysisTask)
            .where(AnalysisTask.id == task_id)
            .options(
                selectinload(AnalysisTask.items).selectinload(
                    AnalysisItem.artifacts
                ),
                selectinload(AnalysisTask.artifacts),
            )
        )
        with self.sessions() as session:
            task = session.scalar(statement)
            if task is None:
                raise NotFoundError("analysis task", task_id)
            return self._serialize_task(task, include_paths=include_paths)

    def _serialize_task(
        self, task: AnalysisTask, *, include_paths: bool
    ) -> dict[str, Any]:
        items = []
        for item in sorted(task.items, key=lambda current: current.source_index):
            artifacts = [
                self._serialize_artifact(artifact)
                for artifact in item.artifacts
            ]
            mask_available = any(
                artifact["kind"] in {"mask", "mask_overlay"}
                for artifact in artifacts
            )
            item_data: dict[str, Any] = {
                "id": item.id,
                "status": item.status,
                "source_name": item.source_name,
                "source_index": item.source_index,
                "page_number": item.page_number,
                "width": item.width,
                "height": item.height,
                "sha256": item.image_sha256,
                "prediction": item.prediction,
                "score_generated": item.score_generated,
                "score_semantics": (
                    SCORE_SEMANTICS if item.score_generated is not None else None
                ),
                "threshold": item.threshold,
                "risk_level": risk_level_for_score(item.score_generated),
                "risk_level_semantics": RISK_LEVEL_SEMANTICS,
                "risk_level_version": RISK_LEVEL_VERSION,
                "risk_level_is_experimental": True,
                "mask_available": mask_available,
                "mask_coverage": item.mask_coverage,
                "localization_message": (
                    None
                    if mask_available
                    else "当前版本不提供区域定位"
                ),
                "artifacts": artifacts,
                "error": (
                    {
                        "code": item.error_code,
                        "message": item.error_message,
                    }
                    if item.error_code
                    else None
                ),
            }
            if include_paths:
                item_data["image_path"] = item.image_path
                for artifact in item_data["artifacts"]:
                    matching = next(
                        source
                        for source in item.artifacts
                        if source.id == artifact["id"]
                    )
                    artifact["path"] = matching.path
            items.append(item_data)

        scored_items = [
            item for item in items if item["score_generated"] is not None
        ]
        overall_item = (
            max(scored_items, key=lambda item: item["score_generated"])
            if scored_items
            else None
        )
        overall_score = (
            overall_item["score_generated"] if overall_item else None
        )
        report_available = any(
            artifact.kind == "report" and artifact.item_id is None
            for artifact in task.artifacts
        )

        result: dict[str, Any] = {
            "schema_version": "1.0",
            "task_id": task.id,
            "status": task.status,
            "input": {
                "filename": task.original_filename,
                "extension": task.extension,
                "media_type": task.media_type,
                "sha256": task.source_sha256,
            },
            "options": {"localize": task.localize_requested},
            "model": (
                {
                    "name": task.model_name,
                    "version": task.model_version,
                    "weight_sha256": task.model_weight_sha256,
                    "threshold": task.model_threshold,
                    "runtime": task.model_runtime,
                    "device": (
                        device_from_runtime(task.model_runtime)
                        if task.model_runtime is not None
                        else None
                    ),
                    "is_mock": task.model_is_mock,
                }
                if task.model_name
                else None
            ),
            "summary": {
                "total": len(items),
                "succeeded": sum(
                    item["status"] == ItemStatus.SUCCEEDED for item in items
                ),
                "failed": sum(
                    item["status"] == ItemStatus.FAILED for item in items
                ),
                "generated": sum(
                    item["prediction"] == "generated" for item in items
                ),
                "original": sum(
                    item["prediction"] == "original" for item in items
                ),
                "score_generated": overall_score,
                "score_semantics": (
                    SCORE_SEMANTICS if overall_score is not None else None
                ),
                "prediction": (
                    overall_item["prediction"] if overall_item else None
                ),
                "risk_level": risk_level_for_score(overall_score),
                "risk_level_semantics": RISK_LEVEL_SEMANTICS,
                "risk_level_version": RISK_LEVEL_VERSION,
                "risk_level_is_experimental": True,
            },
            "items": items,
            "artifacts": [
                self._serialize_artifact(artifact)
                for artifact in task.artifacts
                if artifact.item_id is None
            ],
            "report_available": report_available,
            "report_url": (
                f"/api/v1/analyses/{task.id}/report"
                if report_available
                else None
            ),
            "warnings": (
                [
                    "Development mock inference was used. "
                    "This result has no detection validity."
                ]
                if task.model_is_mock
                else []
            ),
            "error": (
                {"code": task.error_code, "message": task.error_message}
                if task.error_code
                else None
            ),
            "created_at": _iso(task.created_at),
            "updated_at": _iso(task.updated_at),
            "completed_at": _iso(task.completed_at),
        }
        if include_paths:
            result["source_path"] = task.source_path
            for artifact in result["artifacts"]:
                matching = next(
                    source
                    for source in task.artifacts
                    if source.id == artifact["id"]
                )
                artifact["path"] = matching.path
        return result

    @staticmethod
    def _serialize_artifact(artifact: Artifact) -> dict[str, Any]:
        return {
            "id": artifact.id,
            "kind": artifact.kind,
            "media_type": artifact.media_type,
            "filename": artifact.filename,
            "url": f"/api/v1/artifacts/{artifact.id}",
        }

    def delete_task(self, task_id: str) -> None:
        with self.sessions.begin() as session:
            task = session.get(AnalysisTask, task_id)
            if task is None:
                raise NotFoundError("analysis task", task_id)
            session.execute(
                delete(AnalysisTask).where(AnalysisTask.id == task_id)
            )
