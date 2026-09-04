"""Task-isolated local artifact storage."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from typing import BinaryIO
from uuid import uuid4

from backend.blotguard.core.errors import AppError


class LocalStorage:
    def __init__(self, root: Path, max_upload_bytes: int):
        self.root = root.resolve()
        self.max_upload_bytes = max_upload_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        path = (self.root / task_id).resolve()
        if self.root not in path.parents:
            raise ValueError("Unsafe task path")
        return path

    def prepare_task(self, task_id: str) -> Path:
        task_dir = self.task_dir(task_id)
        for name in ("input", "images", "masks", "reports"):
            (task_dir / name).mkdir(parents=True, exist_ok=True)
        return task_dir

    def save_upload(
        self, task_id: str, extension: str, stream: BinaryIO
    ) -> tuple[str, str, int]:
        task_dir = self.prepare_task(task_id)
        destination = task_dir / "input" / f"source.{extension}"
        digest = hashlib.sha256()
        size = 0
        with destination.open("wb") as output:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > self.max_upload_bytes:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise AppError(
                        "FILE_TOO_LARGE",
                        "Uploaded file exceeds the configured size limit",
                        413,
                        {"max_bytes": self.max_upload_bytes},
                    )
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            destination.unlink(missing_ok=True)
            raise AppError("EMPTY_FILE", "Uploaded file is empty", 400)
        return self.relative(destination), digest.hexdigest(), size

    def relative(self, path: str | Path) -> str:
        resolved = Path(path).resolve()
        if self.root not in resolved.parents and resolved != self.root:
            raise ValueError("Path is outside storage root")
        return str(resolved.relative_to(self.root))

    def absolute(self, relative_path: str | Path) -> Path:
        resolved = (self.root / relative_path).resolve()
        if self.root not in resolved.parents:
            raise ValueError("Unsafe storage path")
        return resolved

    def stage_task_delete(self, task_id: str) -> tuple[Path, Path] | None:
        task_dir = self.task_dir(task_id)
        if not task_dir.exists():
            return None
        staged = (self.root / f".delete-{uuid4()}").resolve()
        if self.root not in staged.parents:
            raise ValueError("Unsafe staged deletion path")
        task_dir.rename(staged)
        return task_dir, staged

    @staticmethod
    def finalize_task_delete(staged: tuple[Path, Path] | None) -> None:
        if staged is not None:
            shutil.rmtree(staged[1])

    @staticmethod
    def rollback_task_delete(staged: tuple[Path, Path] | None) -> None:
        if staged is None:
            return
        original, temporary = staged
        if temporary.exists() and not original.exists():
            temporary.rename(original)

    def delete_task(self, task_id: str) -> None:
        staged = self.stage_task_delete(task_id)
        self.finalize_task_delete(staged)
