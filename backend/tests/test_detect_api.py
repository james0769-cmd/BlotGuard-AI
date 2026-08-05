from io import BytesIO

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
        "score_generated": 0.5621765008857981,
        "score_semantics": "uncalibrated_sigmoid_risk_score",
        "prediction": "generated",
        "threshold": 0.5,
        "model_name": "detector",
        "model_version": "detector-v1",
        "weight_sha256": "abc123",
        "is_mock": False,
        "mask_available": False,
        "mask_image_url": None,
        "suspect_regions": [],
        "localization_message": "当前版本不提供区域定位",
    }
