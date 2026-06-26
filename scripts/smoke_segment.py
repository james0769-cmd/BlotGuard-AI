#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CODE_DIR = ROOT / "segment-anything-main_lora"
DEFAULT_SAM_CHECKPOINT = DEFAULT_CODE_DIR / "pretrained_weights" / "sam_vit_b_01ec64.pth"
DEFAULT_LORA_WEIGHT = (
    DEFAULT_CODE_DIR
    / "western_blot"
    / "weight_1024"
    / "rank8-img_size1024-vit_b-best_f1.pth"
)
DEFAULT_OUTPUT = ROOT / "outputs" / "smoke_segment_mask.png"


def parse_layers(value):
    if value in (None, "", "all", "none", "null"):
        return None
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def default_image():
    patterns = [
        ROOT / "data" / "western_blots" / "western_blots_dataset" / "synth" / "stylegan2ada" / "*.png",
        ROOT / "data" / "western_blots" / "western_blots_dataset" / "real" / "*.png",
    ]
    for pattern in patterns:
        for path in pattern.parent.glob(pattern.name):
            if path.is_file():
                return path
    return None


def resolve_device(torch, requested):
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")
    return torch.device(requested)


def load_image(cv2, torch, sam, image_path, device):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    old_h, old_w = image.shape[:2]
    image_size = sam.image_encoder.img_size
    scale = image_size / max(old_h, old_w)
    new_w = int(old_w * scale + 0.5)
    new_h = int(old_h * scale + 0.5)
    image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    tensor = torch.as_tensor(image, dtype=torch.float32, device=device).permute(2, 0, 1)
    return sam.preprocess(tensor).unsqueeze(0), (new_h, new_w), (old_h, old_w)


def main():
    parser = argparse.ArgumentParser(description="Smoke test for the LoRA-SAM tamper localizer.")
    parser.add_argument("--code-dir", type=Path, default=DEFAULT_CODE_DIR)
    parser.add_argument("--sam-checkpoint", type=Path, default=DEFAULT_SAM_CHECKPOINT)
    parser.add_argument("--lora-weight", type=Path, default=DEFAULT_LORA_WEIGHT)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-type", default="vit_b")
    parser.add_argument("--image-size", type=int, default=1024)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--lora-layers", default="all")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    sys.path.insert(0, str(args.code_dir.resolve()))

    import cv2
    import numpy as np
    import torch
    import torch.nn as nn
    from segment_anything import sam_model_registry

    class LoRAQKV(nn.Module):
        def __init__(self, qkv, linear_a_q, linear_b_q, linear_a_v, linear_b_v):
            super().__init__()
            self.qkv = qkv
            self.linear_a_q = linear_a_q
            self.linear_b_q = linear_b_q
            self.linear_a_v = linear_a_v
            self.linear_b_v = linear_b_v
            self.dim = qkv.in_features

        def forward(self, x):
            qkv = self.qkv(x)
            qkv[:, :, :, : self.dim] += self.linear_b_q(self.linear_a_q(x))
            qkv[:, :, :, -self.dim :] += self.linear_b_v(self.linear_a_v(x))
            return qkv

    class SegmentLoRASam(nn.Module):
        def __init__(self, sam_model, rank, lora_layers):
            super().__init__()
            self.lora_layers = lora_layers or list(range(len(sam_model.image_encoder.blocks)))
            self.w_As = []
            self.w_Bs = []
            for param in sam_model.image_encoder.parameters():
                param.requires_grad = False
            for index, block in enumerate(sam_model.image_encoder.blocks):
                if index not in self.lora_layers:
                    continue
                qkv = block.attn.qkv
                dim = qkv.in_features
                linear_a_q = nn.Linear(dim, rank, bias=False)
                linear_b_q = nn.Linear(rank, dim, bias=False)
                linear_a_v = nn.Linear(dim, rank, bias=False)
                linear_b_v = nn.Linear(rank, dim, bias=False)
                self.w_As.extend([linear_a_q, linear_a_v])
                self.w_Bs.extend([linear_b_q, linear_b_v])
                block.attn.qkv = LoRAQKV(qkv, linear_a_q, linear_b_q, linear_a_v, linear_b_v)
            self.sam = sam_model

        def load_lora_parameters(self, filename):
            state_dict = torch.load(filename, map_location="cpu")
            for i, module in enumerate(self.w_As):
                module.weight.data.copy_(state_dict[f"w_a_{i:03d}"])
            for i, module in enumerate(self.w_Bs):
                module.weight.data.copy_(state_dict[f"w_b_{i:03d}"])
            sam_state = self.sam.state_dict()
            sam_state.update({key: value for key, value in state_dict.items() if key in sam_state})
            self.sam.load_state_dict(sam_state)

        def forward(self, images):
            image_embeddings = self.sam.image_encoder(images)
            sparse_embeddings, dense_embeddings = self.sam.prompt_encoder(
                points=None,
                boxes=None,
                masks=None,
            )
            mask_prediction, _ = self.sam.mask_decoder(
                image_embeddings=image_embeddings,
                image_pe=self.sam.prompt_encoder.get_dense_pe().to(image_embeddings.device),
                sparse_prompt_embeddings=sparse_embeddings,
                dense_prompt_embeddings=dense_embeddings,
                multimask_output=False,
            )
            return mask_prediction

    image_path = args.image or default_image()
    if image_path is None:
        raise FileNotFoundError("No image was provided and no default western blot image was found.")

    device = resolve_device(torch, args.device)
    sam, _ = sam_model_registry[args.model_type](
        image_size=args.image_size,
        num_classes=3,
        checkpoint=str(args.sam_checkpoint),
    )
    model = SegmentLoRASam(sam, args.rank, parse_layers(args.lora_layers))
    model.load_lora_parameters(str(args.lora_weight))
    model.to(device).eval()

    image_tensor, input_size, original_size = load_image(cv2, torch, model.sam, image_path, device)
    with torch.no_grad():
        low_res_logits = model(image_tensor)
        masks = model.sam.postprocess_masks(low_res_logits, input_size=input_size, original_size=original_size)
        mask_prob = torch.sigmoid(masks)

    mask_np = (mask_prob[0, 0].detach().cpu().numpy() > 0.5).astype(np.uint8) * 255
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), mask_np)

    print(
        json.dumps(
            {
                "task": "segment",
                "image": str(image_path),
                "device": str(device),
                "mask_shape": list(mask_np.shape),
                "mask_mean": float(mask_np.mean() / 255.0),
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
