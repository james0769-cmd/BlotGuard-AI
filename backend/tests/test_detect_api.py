from io import BytesIO

from backend.blotguard import create_app
from backend.blotguard.inference.contracts import DetectionResult


class StubDetector:
    def predict(self, image_path):
        assert image_path.is_file()
        return DetectionResult(
            image=str(image_path),
            device="cpu",
            logit=0.25,
            probability_generated=0.5621765008857981,
            prediction="generated",
            threshold=0.5,
            model_version="detector-v1",
            weight_sha256="abc123",
        )


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
        data={"image": (BytesIO(b"image-bytes"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "task": "detect",
        "image": "sample.png",
        "device": "cpu",
        "logit": 0.25,
        "probability_generated": 0.5621765008857981,
        "prediction": "generated",
        "threshold": 0.5,
        "model_version": "detector-v1",
        "weight_sha256": "abc123",
        "mask_image_url": None,
        "suspect_regions": [],
    }
