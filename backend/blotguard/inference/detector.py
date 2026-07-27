"""Whole-image LoRA-SAM AI-generation detector."""

from __future__ import annotations

from pathlib import Path
import sys

from backend.blotguard.core.config import ModelConfig
from backend.blotguard.domain.contracts import DetectionResult, ModelMetadata
from .common import load_image, resolve_device


class Detector:
    def __init__(self, config: ModelConfig, device: str = "auto"):
        import cv2
        import torch
        import torch.nn as nn

        self.cv2 = cv2
        self.torch = torch
        self.nn = nn
        self.config = config
        self.device = resolve_device(torch, device)
        self.model = self._load_model()

    def _load_model(self):
        torch = self.torch
        nn = self.nn
        config = self.config

        sys.path.insert(0, str(config.code_dir))
        try:
            from classifier.classifier import FCN_Classifier
            from segment_anything import sam_model_registry
        finally:
            sys.path.pop(0)

        class LoRAQKV(nn.Module):
            def __init__(inner_self, qkv, a_q, b_q, a_v, b_v):
                super().__init__()
                inner_self.qkv = qkv
                inner_self.a_q = a_q
                inner_self.b_q = b_q
                inner_self.a_v = a_v
                inner_self.b_v = b_v
                inner_self.dim = qkv.in_features

            def forward(inner_self, x):
                qkv = inner_self.qkv(x)
                qkv[:, :, :, : inner_self.dim] += inner_self.b_q(
                    inner_self.a_q(x)
                )
                qkv[:, :, :, -inner_self.dim :] += inner_self.b_v(
                    inner_self.a_v(x)
                )
                return qkv

        class DetectLoRASam(nn.Module):
            def __init__(inner_self, sam_model):
                super().__init__()
                layers = config.lora_layers
                inner_self.lora_layers = (
                    list(layers)
                    if layers is not None
                    else list(range(len(sam_model.image_encoder.blocks)))
                )
                inner_self.w_As = nn.ModuleList()
                inner_self.w_Bs = nn.ModuleList()
                for parameter in sam_model.image_encoder.parameters():
                    parameter.requires_grad = False
                for index, block in enumerate(sam_model.image_encoder.blocks):
                    if index not in inner_self.lora_layers:
                        continue
                    qkv = block.attn.qkv
                    dim = qkv.in_features
                    a_q = nn.Linear(dim, config.rank, bias=False)
                    b_q = nn.Linear(config.rank, dim, bias=False)
                    a_v = nn.Linear(dim, config.rank, bias=False)
                    b_v = nn.Linear(config.rank, dim, bias=False)
                    inner_self.w_As.extend([a_q, a_v])
                    inner_self.w_Bs.extend([b_q, b_v])
                    block.attn.qkv = LoRAQKV(qkv, a_q, b_q, a_v, b_v)
                inner_self.sam = sam_model
                inner_self.classifier = FCN_Classifier(num_classes=1)

            def load_lora_parameters(inner_self, filename):
                state = torch.load(
                    filename, map_location="cpu", weights_only=True
                )
                for index, module in enumerate(inner_self.w_As):
                    module.weight.data.copy_(state[f"w_a_{index:03d}"])
                for index, module in enumerate(inner_self.w_Bs):
                    module.weight.data.copy_(state[f"w_b_{index:03d}"])
                classifier_state = {
                    key.removeprefix("classifier."): value
                    for key, value in state.items()
                    if key.startswith("classifier.")
                }
                inner_self.classifier.load_state_dict(
                    classifier_state, strict=False
                )

            def forward(inner_self, images):
                embeddings = inner_self.sam.image_encoder(images)
                return inner_self.classifier(embeddings)

        sam, _ = sam_model_registry[config.model_type](
            image_size=config.image_size,
            num_classes=3,
            checkpoint=str(config.sam_checkpoint),
        )
        model = DetectLoRASam(sam)
        model.load_lora_parameters(str(config.lora_weight))
        return model.to(self.device).eval()

    def predict(self, image_path: str | Path) -> DetectionResult:
        image_tensor, _, _ = load_image(
            self.cv2,
            self.torch,
            self.model.sam,
            Path(image_path),
            self.device,
            self.config.preprocess_mode,
        )
        with self.torch.inference_mode():
            logit = self.model(image_tensor).flatten()[0]
            score = float(self.torch.sigmoid(logit).item())

        return DetectionResult(
            prediction=(
                "generated" if score > self.config.threshold else "original"
            ),
            score_generated=score,
            threshold=self.config.threshold,
            logit=float(logit.detach().cpu()),
            model=ModelMetadata(
                name="western-blot-aigc-detector",
                version=self.config.version,
                weight_sha256=self.config.weight_sha256,
                threshold=self.config.threshold,
                runtime=f"pytorch:{self.device}",
            ),
        )
