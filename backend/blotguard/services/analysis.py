"""End-to-end analysis task orchestration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from backend.blotguard.core.config import RuntimeConfig
from backend.blotguard.core.errors import AppError
from backend.blotguard.domain.contracts import ItemStatus, TaskStatus
from backend.blotguard.inference.provider import (
    InferenceProvider,
    ModelUnavailableError,
)
from backend.blotguard.persistence.repository import AnalysisRepository
from .extraction import ExtractionService
from .reporting import ReportService
from .storage import LocalStorage


class AnalysisService:
    def __init__(
        self,
        config: RuntimeConfig,
        repository: AnalysisRepository,
        storage: LocalStorage,
        extractor: ExtractionService,
        inference: InferenceProvider,
        reports: ReportService,
    ):
        self.config = config
        self.repository = repository
        self.storage = storage
        self.extractor = extractor
        self.inference = inference
        self.reports = reports
        self.executor = ThreadPoolExecutor(
            max_workers=config.max_workers,
            thread_name_prefix="blotguard-analysis",
        )

    def submit(
        self,
        *,
        filename: str,
        media_type: str,
        stream: BinaryIO,
        localize: bool,
    ) -> dict:
        if localize and not self.config.localizer.enabled:
            raise AppError(
                "LOCALIZATION_NOT_AVAILABLE",
                "Forgery localization is not enabled for this model version",
                422,
            )
        extension = self.extractor.validate_extension(filename)
        task_id = str(uuid4())
        source_path, source_sha256, _ = self.storage.save_upload(
            task_id, extension, stream
        )
        try:
            self.repository.create_task(
                task_id=task_id,
                original_filename=Path(filename).name,
                extension=extension,
                media_type=media_type or "application/octet-stream",
                source_sha256=source_sha256,
                source_path=source_path,
                localize_requested=localize,
            )
        except Exception:
            self.storage.delete_task(task_id)
            raise

        if self.config.execution_mode == "inline":
            self.run(task_id)
        else:
            self.executor.submit(self.run, task_id)
        return self.repository.task_detail(task_id)

    def run(self, task_id: str) -> None:
        try:
            task = self.repository.task_detail(task_id, include_paths=True)
            extension = Path(task["source_path"]).suffix.lstrip(".").lower()
            self.repository.set_task_status(task_id, TaskStatus.EXTRACTING)
            images = self.extractor.extract(
                task_id,
                task["source_path"],
                extension,
                task["input"]["filename"],
            )
            item_ids = self.repository.create_items(task_id, images)
            for item_id, image in zip(item_ids, images, strict=True):
                self.repository.create_artifact(
                    task_id,
                    item_id=item_id,
                    kind="extracted_image",
                    path=image.path,
                    media_type="image/png",
                    filename=f"image-{image.source_index:04d}.png",
                )

            self.repository.set_task_status(task_id, TaskStatus.INFERENCING)
            detector = self.inference.detector()
            success_count = 0
            for item_id, image in zip(item_ids, images, strict=True):
                try:
                    result = detector.predict(self.storage.absolute(image.path))
                    self.repository.record_detection(task_id, item_id, result)
                    success_count += 1
                except Exception as exc:
                    self.repository.record_item_failure(
                        item_id, "INFERENCE_FAILED", str(exc)
                    )

            if success_count == 0:
                raise AppError(
                    "ALL_ITEMS_FAILED",
                    "Inference failed for every extracted image",
                    500,
                )

            self.repository.set_task_status(task_id, TaskStatus.REPORTING)
            report_task = self.repository.task_detail(
                task_id, include_paths=True
            )
            report_path = self.reports.generate(report_task)
            self.repository.create_artifact(
                task_id,
                kind="report",
                path=report_path,
                media_type="application/pdf",
                filename=f"blotguard-report-{task_id}.pdf",
            )
            self.repository.set_task_status(task_id, TaskStatus.SUCCEEDED)
        except ModelUnavailableError as exc:
            self._fail(task_id, "MODEL_UNAVAILABLE", str(exc))
        except AppError as exc:
            self._fail(task_id, exc.code, exc.message)
        except Exception as exc:
            self._fail(task_id, "INTERNAL_ERROR", str(exc))

    def _fail(self, task_id: str, code: str, message: str) -> None:
        try:
            self.repository.set_task_status(
                task_id,
                TaskStatus.FAILED,
                error_code=code,
                error_message=message,
            )
        except Exception:
            pass

    def get(self, task_id: str) -> dict:
        return self.repository.task_detail(task_id)

    def delete(self, task_id: str) -> None:
        task = self.repository.task_detail(task_id)
        if task["status"] not in {
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            raise AppError(
                "TASK_NOT_TERMINAL",
                "Only completed, failed, or cancelled tasks can be deleted",
                409,
            )
        self.repository.delete_task(task_id)
        self.storage.delete_task(task_id)
