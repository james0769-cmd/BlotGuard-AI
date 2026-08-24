"""Typed runtime configuration loaded from YAML and environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"


@dataclass(frozen=True)
class ModelConfig:
    enabled: bool
    code_dir: Path
    sam_checkpoint: Path
    lora_weight: Path
    model_type: str
    image_size: int
    rank: int
    lora_layers: tuple[int, ...] | None
    threshold: float
    preprocess_mode: str
    version: str
    weight_sha256: str

    def missing_assets(self) -> list[Path]:
        if not self.enabled:
            return []
        return [
            path
            for path in (self.code_dir, self.sam_checkpoint, self.lora_weight)
            if not path.exists()
        ]


@dataclass(frozen=True)
class RuntimeConfig:
    project_root: Path
    storage_root: Path
    database_url: str
    execution_mode: str
    max_workers: int
    max_upload_bytes: int
    max_images_per_file: int
    max_image_pixels: int
    min_image_side: int
    allowed_extensions: tuple[str, ...]
    allowed_origins: tuple[str, ...]
    report_title: str
    task_retention_days: int
    inference_mode: str
    device: str
    auth_secret_key: str
    auth_token_ttl_seconds: int
    auth_registration_enabled: bool
    detector: ModelConfig
    localizer: ModelConfig

    @property
    def detect(self) -> ModelConfig:
        """Backward-compatible name used by the original model API."""
        return self.detector

    @property
    def segment(self) -> ModelConfig:
        """Backward-compatible name used by the original model API."""
        return self.localizer


def _resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _database_url(project_root: Path, value: str) -> str:
    if not value.startswith("sqlite:///"):
        return value
    raw_path = value.removeprefix("sqlite:///")
    resolved = _resolve_path(project_root, raw_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved}"


def _model_config(project_root: Path, values: dict[str, Any]) -> ModelConfig:
    layers = values.get("lora_layers")
    return ModelConfig(
        enabled=bool(values.get("enabled", True)),
        code_dir=_resolve_path(project_root, values["code_dir"]),
        sam_checkpoint=_resolve_path(project_root, values["sam_checkpoint"]),
        lora_weight=_resolve_path(project_root, values["lora_weight"]),
        model_type=str(values["model_type"]),
        image_size=int(values["image_size"]),
        rank=int(values["rank"]),
        lora_layers=None if layers is None else tuple(int(layer) for layer in layers),
        threshold=float(values.get("threshold", 0.5)),
        preprocess_mode=str(values.get("preprocess_mode", "stretch")),
        version=str(values["version"]),
        weight_sha256=str(values["weight_sha256"]),
    )


def _environment_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def load_runtime_config(config_path: str | Path | None = None) -> RuntimeConfig:
    path = Path(
        config_path or os.environ.get("BLOTGUARD_CONFIG", DEFAULT_CONFIG_PATH)
    ).expanduser().resolve()
    with path.open("r", encoding="utf-8") as stream:
        values = yaml.safe_load(stream)

    project_root = _resolve_path(path.parent, values.get("project_root", ".."))
    app = values["app"]
    auth = values.get("auth", {})
    inference = values["inference"]

    database_value = os.environ.get(
        "BLOTGUARD_DATABASE_URL", str(app["database_url"])
    )
    storage_value = os.environ.get(
        "BLOTGUARD_STORAGE_ROOT", str(app["storage_root"])
    )
    origins = os.environ.get("BLOTGUARD_ALLOWED_ORIGINS")
    allowed_origins = (
        tuple(item.strip() for item in origins.split(",") if item.strip())
        if origins
        else tuple(str(item) for item in app.get("allowed_origins", ()))
    )

    execution_mode = os.environ.get(
        "BLOTGUARD_EXECUTION_MODE", str(app.get("execution_mode", "thread"))
    )
    inference_mode = os.environ.get(
        "BLOTGUARD_INFERENCE_MODE", str(inference.get("mode", "real"))
    )
    device = os.environ.get(
        "BLOTGUARD_DEVICE", str(inference.get("device", "auto"))
    )
    auth_secret_key = os.environ.get(
        "BLOTGUARD_AUTH_SECRET_KEY",
        str(auth.get("secret_key", "blotguard-local-development-only")),
    )
    auth_token_ttl_seconds = int(
        os.environ.get(
            "BLOTGUARD_AUTH_TOKEN_TTL_SECONDS",
            str(auth.get("token_ttl_seconds", 28800)),
        )
    )
    auth_registration_enabled = _environment_bool(
        "BLOTGUARD_AUTH_REGISTRATION_ENABLED",
        bool(auth.get("registration_enabled", True)),
    )
    task_retention_days = int(app.get("task_retention_days", 30))

    if execution_mode not in {"inline", "thread"}:
        raise ValueError("execution_mode must be 'inline' or 'thread'")
    if inference_mode not in {"real", "mock"}:
        raise ValueError("inference mode must be 'real' or 'mock'")
    if not auth_secret_key.strip():
        raise ValueError("auth secret key must not be empty")
    if auth_token_ttl_seconds <= 0:
        raise ValueError("auth token TTL must be positive")
    if task_retention_days <= 0:
        raise ValueError("task retention days must be positive")

    return RuntimeConfig(
        project_root=project_root,
        storage_root=_resolve_path(project_root, storage_value),
        database_url=_database_url(project_root, database_value),
        execution_mode=execution_mode,
        max_workers=int(app.get("max_workers", 2)),
        max_upload_bytes=int(app["max_upload_bytes"]),
        max_images_per_file=int(app["max_images_per_file"]),
        max_image_pixels=int(app["max_image_pixels"]),
        min_image_side=int(app["min_image_side"]),
        allowed_extensions=tuple(
            str(item).lower() for item in app["allowed_extensions"]
        ),
        allowed_origins=allowed_origins,
        report_title=str(app["report_title"]),
        task_retention_days=task_retention_days,
        inference_mode=inference_mode,
        device=device,
        auth_secret_key=auth_secret_key,
        auth_token_ttl_seconds=auth_token_ttl_seconds,
        auth_registration_enabled=auth_registration_enabled,
        detector=_model_config(project_root, inference["detector"]),
        localizer=_model_config(project_root, inference["localizer"]),
    )
