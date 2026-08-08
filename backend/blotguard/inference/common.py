"""Shared image preprocessing and device helpers."""

from __future__ import annotations


def resolve_device(torch, requested: str):
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    return torch.device(requested)


def resized_dimensions(old_h: int, old_w: int, image_size: int, mode: str):
    if mode == "stretch":
        return image_size, image_size
    if mode == "longest_side":
        scale = image_size / max(old_h, old_w)
        return int(old_h * scale + 0.5), int(old_w * scale + 0.5)
    raise ValueError(f"Unsupported preprocess mode: {mode}")


def load_image(cv2, torch, sam, image_path, device, mode: str):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    old_h, old_w = image.shape[:2]
    image_size = int(sam.image_encoder.img_size)
    new_h, new_w = resized_dimensions(old_h, old_w, image_size, mode)

    image = cv2.resize(
        image, (new_w, new_h), interpolation=cv2.INTER_AREA
    )

    tensor = torch.as_tensor(
        image, dtype=torch.float32, device=device
    ).permute(2, 0, 1)
    return sam.preprocess(tensor).unsqueeze(0), (new_h, new_w), (old_h, old_w)
