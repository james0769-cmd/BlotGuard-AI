#!/usr/bin/env python
import argparse
from dataclasses import replace
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.blotguard.core.config import load_runtime_config
from backend.blotguard.inference.common import parse_layers
from backend.blotguard.inference.detector import Detector


DEFAULT_CONFIG = load_runtime_config()


def default_image():
    patterns = [
        DEFAULT_CONFIG.data_root
        / "western_blots"
        / "western_blots_dataset"
        / "real"
        / "*.png",
        DEFAULT_CONFIG.data_root
        / "western_blots"
        / "western_blots_dataset"
        / "synth"
        / "stylegan2ada"
        / "*.png",
        DEFAULT_CONFIG.detect.code_dir / "original_image.png",
    ]
    for pattern in patterns:
        for path in pattern.parent.glob(pattern.name):
            if path.is_file():
                return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test for the LoRA-SAM AIGC detector."
    )
    parser.add_argument("--code-dir", type=Path, default=DEFAULT_CONFIG.detect.code_dir)
    parser.add_argument(
        "--sam-checkpoint", type=Path, default=DEFAULT_CONFIG.detect.sam_checkpoint
    )
    parser.add_argument(
        "--lora-weight", type=Path, default=DEFAULT_CONFIG.detect.lora_weight
    )
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--model-type", default=DEFAULT_CONFIG.detect.model_type)
    parser.add_argument("--image-size", type=int, default=DEFAULT_CONFIG.detect.image_size)
    parser.add_argument("--rank", type=int, default=DEFAULT_CONFIG.detect.rank)
    parser.add_argument("--lora-layers", default="0,1,2,3,4,5")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    image_path = args.image or default_image()
    if image_path is None:
        raise FileNotFoundError(
            "No image was provided and no default western blot image was found."
        )

    config = replace(
        DEFAULT_CONFIG.detect,
        code_dir=args.code_dir,
        sam_checkpoint=args.sam_checkpoint,
        lora_weight=args.lora_weight,
        model_type=args.model_type,
        image_size=args.image_size,
        rank=args.rank,
        lora_layers=parse_layers(args.lora_layers),
    )
    result = Detector(config, args.device).predict(image_path)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
