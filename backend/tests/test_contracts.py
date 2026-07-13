from backend.blotguard.inference.contracts import DetectionResult, LocalizationResult


def test_detection_result_wire_shape():
    result = DetectionResult(
        "image.png",
        "cpu",
        0.1,
        0.5,
        "original",
        0.5,
        "detector-v1",
        "abc123",
    )

    assert result.to_dict() == {
        "task": "detect",
        "image": "image.png",
        "device": "cpu",
        "logit": 0.1,
        "probability_generated": 0.5,
        "prediction": "original",
        "threshold": 0.5,
        "model_version": "detector-v1",
        "weight_sha256": "abc123",
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
