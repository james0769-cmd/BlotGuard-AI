"""Real Detector inference endpoint."""

from pathlib import Path
from tempfile import TemporaryDirectory

from flask import current_app, request

from backend.blotguard.core.config import load_runtime_config
from backend.blotguard.inference.detector import Detector
from . import api


def _detector():
    detector = current_app.extensions.get("blotguard_detector")
    if detector is None:
        config = load_runtime_config().detect
        if not config.enabled:
            raise RuntimeError("Detector is disabled.")
        detector = Detector(config, current_app.config.get("MODEL_DEVICE", "auto"))
        current_app.extensions["blotguard_detector"] = detector
    return detector


@api.post("/detect")
def detect():
    image = request.files.get("image")
    if image is None or not image.filename:
        return {"error": "image file is required"}, 400

    suffix = Path(image.filename).suffix or ".img"
    with TemporaryDirectory(prefix="blotguard-") as temp_dir:
        image_path = Path(temp_dir) / f"input{suffix}"
        image.save(image_path)
        result = _detector().predict(image_path).to_dict()

    result["image"] = image.filename
    result["mask_image_url"] = None
    result["suspect_regions"] = []
    return result
