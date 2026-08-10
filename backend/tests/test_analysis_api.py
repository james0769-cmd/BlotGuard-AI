from io import BytesIO
import zipfile

from PIL import Image

from backend.blotguard.domain.risk import risk_level_for_score


def test_png_analysis_report_artifact_and_delete(client, png_bytes):
    response = client.post(
        "/api/v1/analyses",
        data={"file": (BytesIO(png_bytes), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    task = response.get_json()
    assert task["status"] == "succeeded"
    assert task["summary"] == {
        "failed": 0,
        "generated": task["summary"]["generated"],
        "original": task["summary"]["original"],
        "succeeded": 1,
        "total": 1,
    }
    assert task["model"]["is_mock"] is True
    assert task["model"]["device"] == "cpu"
    assert task["items"][0]["score_semantics"] == (
        "uncalibrated_sigmoid_risk_score"
    )
    assert task["items"][0]["mask_available"] is False
    assert task["items"][0]["localization_message"] == (
        "当前版本不提供区域定位"
    )
    assert task["items"][0]["artifacts"][0]["kind"] == "extracted_image"

    task_id = task["task_id"]
    report = client.get(f"/api/v1/analyses/{task_id}/report")
    assert report.status_code == 200
    assert report.mimetype == "application/pdf"
    assert report.data.startswith(b"%PDF")

    image_url = task["items"][0]["artifacts"][0]["url"]
    image = client.get(image_url)
    assert image.status_code == 200
    assert image.mimetype == "image/png"

    deleted = client.delete(f"/api/v1/analyses/{task_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/analyses/{task_id}").status_code == 404


def test_docx_media_extraction(client, png_bytes):
    document = BytesIO()
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("word/media/image1.png", png_bytes)
    document.seek(0)

    response = client.post(
        "/api/v1/analyses",
        data={"file": (document, "paper.docx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    task = response.get_json()
    assert task["status"] == "succeeded"
    assert task["summary"]["total"] == 1
    assert task["items"][0]["source_name"] == "image1.png"


def test_rejects_unsupported_extension(client, png_bytes):
    response = client.post(
        "/api/v1/analyses",
        data={"file": (BytesIO(png_bytes), "legacy.doc")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_rejects_signature_mismatch(client):
    response = client.post(
        "/api/v1/analyses",
        data={"file": (BytesIO(b"not a png"), "fake.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    task = response.get_json()
    assert task["status"] == "failed"
    assert task["error"]["code"] == "FILE_SIGNATURE_MISMATCH"


def test_rejects_localization_until_model_is_confirmed(client, png_bytes):
    response = client.post(
        "/api/v1/analyses",
        data={
            "file": (BytesIO(png_bytes), "sample.png"),
            "localize": "true",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == (
        "LOCALIZATION_NOT_AVAILABLE"
    )


def test_frontend_compat_login_upload_result_report(client, png_bytes):
    login = client.post(
        "/api/auth/login",
        json={"username": "zhao", "password": "anything"},
    )
    assert login.status_code == 200
    assert login.get_json()["user"]["username"] == "zhao"

    upload = client.post(
        "/api/tasks/upload",
        data={"file": (BytesIO(png_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    task = upload.get_json()
    assert task["file_name"] == "sample.png"
    assert task["file_size"] == len(png_bytes)
    assert task["status"] == "completed"
    assert task["progress"] == 100

    task_id = task["task_id"]
    polled = client.get(f"/api/tasks/{task_id}")
    assert polled.status_code == 200
    assert polled.get_json()["status"] == "completed"

    result = client.get(f"/api/tasks/{task_id}/result")
    assert result.status_code == 200
    payload = result.get_json()
    assert payload["task_id"] == task_id
    assert payload["filename"] == "sample.png"
    assert payload["original_image_url"].startswith("/api/v1/artifacts/")
    assert payload["mask_available"] is False
    assert payload["mask_image_url"] is None
    assert payload["localization_message"] == "当前版本不提供区域定位"
    assert payload["overall_score"] is not None
    assert payload["score_generated"] == payload["overall_score"]
    assert payload["score_semantics"] == (
        "uncalibrated_sigmoid_risk_score"
    )
    assert payload["prediction"] in {"generated", "original"}
    assert payload["threshold"] == 0.5
    assert payload["risk_level"] == risk_level_for_score(
        payload["score_generated"]
    )
    assert payload["overall_risk"] == payload["risk_level"]
    assert payload["risk_level_semantics"] == (
        "experimental_class_balanced_calibrated_risk"
    )
    assert payload["risk_level_version"] == (
        "experimental-platt-balanced-v1"
    )
    assert payload["risk_level_is_experimental"] is True
    assert payload["suspect_regions"] == []
    assert payload["model_probabilities"] == []
    assert payload["model_version"] == "mock-v1"
    assert payload["weight_sha256"] == "not-a-real-model"
    assert payload["device"] == "cpu"
    assert "实验性五级风险" in payload["conclusion"]
    assert "DDPM/Pix2Pix" in payload["conclusion"]

    report = client.get(f"/api/tasks/{task_id}/report")
    assert report.status_code == 200
    assert report.mimetype == "application/pdf"
    assert report.data.startswith(b"%PDF")


def test_frontend_compat_errors_are_flat(client):
    response = client.post(
        "/api/tasks/upload",
        data={"file": (BytesIO(b"not a png"), "fake.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task_id = response.get_json()["task_id"]
    task = client.get(f"/api/tasks/{task_id}").get_json()
    assert task["status"] == "failed"
    assert task["error_message"] == (
        "File contents do not match the filename extension"
    )

    missing = client.get("/api/tasks/not-a-task")
    assert missing.status_code == 404
    payload = missing.get_json()
    assert payload["error"] == "NOT_FOUND"
    assert "message" in payload


def test_tiff_upload_is_supported(client):
    stream = BytesIO()
    Image.new("RGB", (128, 128), color=(210, 210, 210)).save(
        stream, format="TIFF"
    )
    data = stream.getvalue()

    response = client.post(
        "/api/tasks/upload",
        data={"file": (BytesIO(data), "sample.tiff")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task = response.get_json()
    assert task["file_name"] == "sample.tiff"
    assert task["status"] == "completed"
