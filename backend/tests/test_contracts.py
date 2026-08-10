from backend.blotguard.domain.contracts import DetectionResult, ModelMetadata
from backend.blotguard.inference.contracts import LocalizationResult


def test_detection_result_wire_shape():
    result = DetectionResult(
        prediction="original",
        score_generated=0.5,
        threshold=0.5,
        logit=0.1,
        model=ModelMetadata(
            name="detector",
            version="detector-v1",
            weight_sha256="abc123",
            threshold=0.5,
            runtime="pytorch:cpu",
        ),
    )

    assert result.to_dict() == {
        "task": "detect",
        "device": "cpu",
        "logit": 0.1,
        "score_generated": 0.5,
        "score_semantics": "uncalibrated_sigmoid_risk_score",
        "prediction": "original",
        "threshold": 0.5,
        "model_name": "detector",
        "model_version": "detector-v1",
        "weight_sha256": "abc123",
        "is_mock": False,
    }


def test_localization_result_wire_shape():
    result = LocalizationResult("image.png", "cpu", [10, 20], 0.25, "mask.png")

    assert result.to_dict() == {
        "task": "segment",
        "image": "image.png",
        "device": "cpu",
        "mask_shape": [10, 20],
        "mask_mean": 0.25,
        "output": "mask.png",
    }
