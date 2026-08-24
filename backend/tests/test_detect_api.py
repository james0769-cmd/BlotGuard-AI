from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter

from backend.blotguard import create_app
from backend.blotguard.domain.contracts import DetectionResult, ModelMetadata


class StubDetector:
    def predict(self, image_path):
        assert image_path.is_file()
        return DetectionResult(
            prediction="generated",
            score_generated=0.5621765008857981,
            threshold=0.5,
            logit=0.25,
            model=ModelMetadata(
                name="detector",
                version="detector-v1",
                weight_sha256="abc123",
                threshold=0.5,
                runtime="pytorch:cpu",
            ),
        )


def _blot_png() -> bytes:
    stream = BytesIO()
    image = Image.new("RGB", (256, 256), color=(225, 225, 225))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 95, 105, 120), radius=8, fill=(30, 30, 30))
    draw.rounded_rectangle((145, 95, 225, 120), radius=8, fill=(35, 35, 35))
    image.filter(ImageFilter.GaussianBlur(3)).save(stream, format="PNG")
    return stream.getvalue()


def test_detect_requires_image():
    client = create_app({"TESTING": True}).test_client()

    response = client.post("/api/v1/detect")

    assert response.status_code == 400
    assert response.get_json() == {"error": "image file is required"}


def test_detect_returns_real_contract():
    app = create_app({"TESTING": True})
    app.extensions["blotguard_detector"] = StubDetector()
    client = app.test_client()

    response = client.post(
        "/api/v1/detect",
        data={"image": (BytesIO(_blot_png()), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "task": "detect",
        "image": "sample.png",
        "device": "cpu",
        "logit": 0.25,
        "score_generated": 0.5621765008857981,
        "score_semantics": "uncalibrated_sigmoid_risk_score",
        "prediction": "generated",
        "threshold": 0.5,
        "model_name": "detector",
        "model_version": "detector-v1",
        "weight_sha256": "abc123",
        "is_mock": False,
        "applicable": True,
        "domain_label": "western_blot",
        "domain_message": "输入通过 Western Blot 图像域预检",
        "mask_available": False,
        "mask_image_url": None,
        "suspect_regions": [],
        "localization_message": "当前版本不提供区域定位",
    }
