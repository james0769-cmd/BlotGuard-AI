#!/usr/bin/env python
import argparse
from dataclasses import replace
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard.core.config import load_runtime_config
from backend.blotguard.inference.localizer import Localizer


DEFAULT_CONFIG = load_runtime_config()
DEFAULT_OUTPUT = ROOT / "outputs" / "smoke_segment_mask.png"
FIXTURE_IMAGE = ROOT / "tests" / "fixtures" / "western_blot_sample.png"


def default_image():
    return FIXTURE_IMAGE if FIXTURE_IMAGE.is_file() else None


def parse_layers(value: str) -> tuple[int, ...] | None:
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    return tuple(int(layer.strip()) for layer in value.split(","))


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test for the LoRA-SAM tamper localizer."
    )
    parser.add_argument("--code-dir", type=Path, default=DEFAULT_CONFIG.segment.code_dir)
    parser.add_argument(
        "--sam-checkpoint", type=Path, default=DEFAULT_CONFIG.segment.sam_checkpoint
    )
    parser.add_argument(
        "--lora-weight", type=Path, default=DEFAULT_CONFIG.segment.lora_weight
    )
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-type", default=DEFAULT_CONFIG.segment.model_type)
    parser.add_argument("--image-size", type=int, default=DEFAULT_CONFIG.segment.image_size)
    parser.add_argument("--rank", type=int, default=DEFAULT_CONFIG.segment.rank)
    parser.add_argument("--lora-layers", default="all")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    image_path = args.image or default_image()
    if image_path is None:
        raise FileNotFoundError(
            "No image was provided and no default western blot image was found."
        )

    config = replace(
        DEFAULT_CONFIG.segment,
        code_dir=args.code_dir,
        sam_checkpoint=args.sam_checkpoint,
        lora_weight=args.lora_weight,
        model_type=args.model_type,
        image_size=args.image_size,
        rank=args.rank,
        lora_layers=parse_layers(args.lora_layers),
    )
    result = Localizer(config, args.device).predict(image_path, args.output)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
