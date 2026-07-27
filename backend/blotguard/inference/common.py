"""Shared image preprocessing and device helpers."""

from __future__ import annotations


def resolve_device(torch, requested: str):
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    return torch.device(requested)


def load_image(cv2, torch, sam, image_path, device, mode: str):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    old_h, old_w = image.shape[:2]
    image_size = int(sam.image_encoder.img_size)

    if mode == "stretch":
        image = cv2.resize(
            image, (image_size, image_size), interpolation=cv2.INTER_AREA
        )
        new_h, new_w = image_size, image_size
    elif mode == "longest_side":
        scale = image_size / max(old_h, old_w)
        new_w = int(old_w * scale + 0.5)
        new_h = int(old_h * scale + 0.5)
        image = cv2.resize(
            image, (new_w, new_h), interpolation=cv2.INTER_AREA
        )
    else:
        raise ValueError(f"Unsupported preprocess mode: {mode}")

    tensor = torch.as_tensor(
        image, dtype=torch.float32, device=device
    ).permute(2, 0, 1)
    return sam.preprocess(tensor).unsqueeze(0), (new_h, new_w), (old_h, old_w)
