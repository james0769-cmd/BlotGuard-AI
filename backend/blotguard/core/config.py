"""Runtime configuration loaded from the repository YAML file."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"


@dataclass(frozen=True)
class InferenceConfig:
    enabled: bool
    code_dir: Path
    sam_checkpoint: Path
    lora_weight: Path
    model_type: str
    image_size: int
    rank: int
    lora_layers: tuple[int, ...] | None
    threshold: float
    version: str
    weight_sha256: str


@dataclass(frozen=True)
class RuntimeConfig:
    project_root: Path
    data_root: Path
    detect: InferenceConfig
    segment: InferenceConfig


def _resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _inference_config(project_root: Path, values: dict[str, Any]) -> InferenceConfig:
    layers = values.get("lora_layers")
    return InferenceConfig(
        enabled=bool(values["enabled"]),
        code_dir=_resolve_path(project_root, values["code_dir"]),
        sam_checkpoint=_resolve_path(project_root, values["sam_checkpoint"]),
        lora_weight=_resolve_path(project_root, values["lora_weight"]),
        model_type=str(values["model_type"]),
        image_size=int(values["image_size"]),
        rank=int(values["rank"]),
        lora_layers=None if layers is None else tuple(int(layer) for layer in layers),
        threshold=float(values["threshold"]),
        version=str(values["version"]),
        weight_sha256=str(values["weight_sha256"]),
    )


def load_runtime_config(config_path: str | Path | None = None) -> RuntimeConfig:
    path = Path(
        config_path or os.environ.get("BLOTGUARD_CONFIG", DEFAULT_CONFIG_PATH)
    ).expanduser().resolve()
    with path.open("r", encoding="utf-8") as stream:
        values = yaml.safe_load(stream)

    project_root = _resolve_path(path.parent, values.get("project_root", ".."))
    return RuntimeConfig(
        project_root=project_root,
        data_root=_resolve_path(project_root, values["data_root"]),
        detect=_inference_config(project_root, values["detect"]),
        segment=_inference_config(project_root, values["segment"]),
    )
