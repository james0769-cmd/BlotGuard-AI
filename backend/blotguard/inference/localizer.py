"""Pixel-level forgery localization adapter."""

from __future__ import annotations

from pathlib import Path
import sys

import cv2
import numpy as np
import torch
import torch.nn as nn

from backend.blotguard.core.config import InferenceConfig
from .common import load_image, resolve_device
from .contracts import LocalizationResult


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


class Localizer:
    def __init__(self, config: InferenceConfig, device: str = "auto"):
        self.config = config
        self.device = resolve_device(torch, device)
        self.model = self._load_model()

    def _load_model(self):
        sys.path.insert(0, str(self.config.code_dir))
        try:
            from segment_anything import sam_model_registry
        finally:
            sys.path.pop(0)

        class SegmentLoRASam(nn.Module):
            def __init__(inner_self, sam_model, rank, lora_layers):
                super().__init__()
                inner_self.lora_layers = lora_layers or list(
                    range(len(sam_model.image_encoder.blocks))
                )
                inner_self.w_As = []
                inner_self.w_Bs = []
                for param in sam_model.image_encoder.parameters():
                    param.requires_grad = False
                for index, block in enumerate(sam_model.image_encoder.blocks):
                    if index not in inner_self.lora_layers:
                        continue
                    qkv = block.attn.qkv
                    dim = qkv.in_features
                    linear_a_q = nn.Linear(dim, rank, bias=False)
                    linear_b_q = nn.Linear(rank, dim, bias=False)
                    linear_a_v = nn.Linear(dim, rank, bias=False)
                    linear_b_v = nn.Linear(rank, dim, bias=False)
                    inner_self.w_As.extend([linear_a_q, linear_a_v])
                    inner_self.w_Bs.extend([linear_b_q, linear_b_v])
                    block.attn.qkv = LoRAQKV(
                        qkv, linear_a_q, linear_b_q, linear_a_v, linear_b_v
                    )
                inner_self.sam = sam_model

            def load_lora_parameters(inner_self, filename):
                state_dict = torch.load(filename, map_location="cpu")
                for i, module in enumerate(inner_self.w_As):
                    module.weight.data.copy_(state_dict[f"w_a_{i:03d}"])
                for i, module in enumerate(inner_self.w_Bs):
                    module.weight.data.copy_(state_dict[f"w_b_{i:03d}"])
                sam_state = inner_self.sam.state_dict()
                sam_state.update(
                    {key: value for key, value in state_dict.items() if key in sam_state}
                )
                inner_self.sam.load_state_dict(sam_state)

            def forward(inner_self, images):
                image_embeddings = inner_self.sam.image_encoder(images)
                sparse_embeddings, dense_embeddings = inner_self.sam.prompt_encoder(
                    points=None,
                    boxes=None,
                    masks=None,
                )
                mask_prediction, _ = inner_self.sam.mask_decoder(
                    image_embeddings=image_embeddings,
                    image_pe=inner_self.sam.prompt_encoder.get_dense_pe().to(
                        image_embeddings.device
                    ),
                    sparse_prompt_embeddings=sparse_embeddings,
                    dense_prompt_embeddings=dense_embeddings,
                    multimask_output=False,
                )
                return mask_prediction

        sam, _ = sam_model_registry[self.config.model_type](
            image_size=self.config.image_size,
            num_classes=3,
            checkpoint=str(self.config.sam_checkpoint),
        )
        model = SegmentLoRASam(
            sam, self.config.rank, list(self.config.lora_layers or ()) or None
        )
        model.load_lora_parameters(str(self.config.lora_weight))
        return model.to(self.device).eval()

    def predict(
        self, image_path: str | Path, output_path: str | Path
    ) -> LocalizationResult:
        image = Path(image_path)
        output = Path(output_path)
        image_tensor, input_size, original_size = load_image(
            cv2, torch, self.model.sam, image, self.device
        )
        with torch.no_grad():
            low_res_logits = self.model(image_tensor)
            masks = self.model.sam.postprocess_masks(
                low_res_logits,
                input_size=input_size,
                original_size=original_size,
            )
            mask_prob = torch.sigmoid(masks)

        mask_np = (
            (mask_prob[0, 0].detach().cpu().numpy() > self.config.threshold).astype(
                np.uint8
            )
            * 255
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output), mask_np)

        return LocalizationResult(
            image=str(image_path),
            device=str(self.device),
            mask_shape=list(mask_np.shape),
            mask_mean=float(mask_np.mean() / 255.0),
            output=str(output_path),
        )
