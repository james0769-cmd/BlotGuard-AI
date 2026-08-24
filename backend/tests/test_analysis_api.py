from dataclasses import replace
from io import BytesIO
import zipfile

from PIL import Image
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from backend.blotguard import create_app
from backend.blotguard.domain.risk import risk_level_for_score


def _docx_with_images(png_bytes: bytes, count: int = 2) -> BytesIO:
    document = BytesIO()
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        for index in range(1, count + 1):
            archive.writestr(f"word/media/image{index}.png", png_bytes)
    document.seek(0)
    return document


def _pdf_with_images(png_bytes: bytes, count: int = 2) -> BytesIO:
    document = BytesIO()
    pdf = canvas.Canvas(document, pagesize=(360, 240))
    for _index in range(count):
        pdf.drawImage(
            ImageReader(BytesIO(png_bytes)),
            20,
            20,
            width=320,
            height=180,
        )
        pdf.showPage()
    pdf.save()
    document.seek(0)
    return document


def _color_decoration_png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (640, 480), color=(214, 238, 248)).save(
        stream, format="PNG"
    )
    return stream.getvalue()


def _unrelated_color_image() -> bytes:
    stream = BytesIO()
    image = Image.new("RGB", (640, 360), color=(205, 225, 245))
    for y in range(180, 360):
        color = (230, max(40, 180 - (y - 180) // 2), 35)
        for x in range(640):
            image.putpixel((x, y), color)
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_png_analysis_report_artifact_and_delete(client, png_bytes):
    response = client.post(
        "/api/v1/analyses",
        data={"file": (BytesIO(png_bytes), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    task = response.get_json()
    assert task["status"] == "succeeded"
    assert task["summary"]["failed"] == 0
    assert task["summary"]["succeeded"] == 1
    assert task["summary"]["total"] == 1
    assert task["summary"]["score_generated"] is not None
    assert task["summary"]["prediction"] in {"generated", "original"}
    assert task["summary"]["risk_level"] == risk_level_for_score(
        task["summary"]["score_generated"]
    )
    assert task["model"]["is_mock"] is True
    assert task["model"]["device"] == "cpu"
    assert task["input"]["extension"] == "png"
    assert task["items"][0]["score_semantics"] == (
        "uncalibrated_sigmoid_risk_score"
    )
    assert task["items"][0]["mask_available"] is False
    assert task["items"][0]["risk_level"] == risk_level_for_score(
        task["items"][0]["score_generated"]
    )
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
    document = _docx_with_images(png_bytes, count=1)

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


def test_frontend_compat_returns_all_docx_images(client, png_bytes):
    response = client.post(
        "/api/tasks/upload",
        data={"file": (_docx_with_images(png_bytes), "paper.docx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task_id = response.get_json()["task_id"]
    result = client.get(f"/api/tasks/{task_id}/result").get_json()

    assert result["file_type"] == "docx"
    assert result["image_count"] == 2
    assert result["result_summary"]["total"] == 2
    assert [item["source_index"] for item in result["items"]] == [1, 2]
    assert all(item["risk_level"] for item in result["items"])
    assert all(item["mask_available"] is False for item in result["items"])
    assert result["report_available"] is True
    assert result["report_url"] == f"/api/tasks/{task_id}/report"

    report = client.get(result["report_url"])
    assert report.status_code == 200
    assert len(PdfReader(BytesIO(report.data)).pages) >= 3


def test_frontend_compat_returns_all_pdf_images(client, png_bytes):
    response = client.post(
        "/api/tasks/upload",
        data={"file": (_pdf_with_images(png_bytes), "paper.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task_id = response.get_json()["task_id"]
    result = client.get(f"/api/tasks/{task_id}/result").get_json()

    assert result["file_type"] == "pdf"
    assert result["image_count"] == 2
    assert result["result_summary"]["total"] == 2
    assert [item["page_number"] for item in result["items"]] == [1, 2]
    assert all(item["original_image_url"] for item in result["items"])
    assert result["risk_level"] == risk_level_for_score(
        max(item["score_generated"] for item in result["items"])
    )
    assert result["report_available"] is True

    report = client.get(result["report_url"])
    assert report.status_code == 200
    assert len(PdfReader(BytesIO(report.data)).pages) >= 3


def test_pdf_decorations_are_not_sent_to_detector(client):
    response = client.post(
        "/api/tasks/upload",
        data={
            "file": (
                _pdf_with_images(_color_decoration_png(), count=1),
                "decorative-paper.pdf",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task = response.get_json()
    assert task["status"] == "failed"
    assert "Western Blot" in task["error_message"]


def test_unrelated_image_is_not_given_an_authenticity_score(client):
    response = client.post(
        "/api/tasks/upload",
        data={
            "file": (BytesIO(_unrelated_color_image()), "landscape.png")
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task_id = response.get_json()["task_id"]
    result = client.get(f"/api/tasks/{task_id}/result").get_json()

    assert result["status"] == "completed"
    assert result["applicable"] is False
    assert result["prediction"] == "not_applicable"
    assert result["domain_label"] == "non_western_blot"
    assert result["score_generated"] is None
    assert result["risk_level"] is None
    assert result["items"][0]["applicable"] is False
    assert "未执行真伪" in result["conclusion"]


def test_mixed_document_only_scores_western_blot_images(client, png_bytes):
    document = BytesIO()
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("word/media/blot.png", png_bytes)
        archive.writestr(
            "word/media/landscape.png", _unrelated_color_image()
        )
    document.seek(0)

    response = client.post(
        "/api/tasks/upload",
        data={"file": (document, "mixed.docx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    task_id = response.get_json()["task_id"]
    result = client.get(f"/api/tasks/{task_id}/result").get_json()

    assert result["image_count"] == 2
    assert result["applicable"] is True
    assert result["score_generated"] is not None
    assert [item["applicable"] for item in result["items"]] == [True, False]
    assert result["result_summary"]["not_applicable"] == 1


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
    registered = client.post(
        "/api/auth/register",
        json={"username": "zhao", "password": "correct-password"},
    )
    assert registered.status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"username": "zhao", "password": "correct-password"},
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
    assert payload["file_type"] == "png"
    assert payload["backend_status"] == "succeeded"
    assert payload["image_count"] == 1
    assert len(payload["items"]) == 1
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
    assert payload["items"][0]["risk_level"] == payload["risk_level"]
    assert payload["items"][0]["score_generated"] == payload[
        "score_generated"
    ]
    assert payload["suspect_regions"] == []
    assert payload["model_probabilities"] == []
    assert payload["model_version"] == "mock-v1"
    assert payload["weight_sha256"] == "not-a-real-model"
    assert payload["device"] == "cpu"
    assert payload["is_mock"] is True
    assert payload["report_available"] is True
    assert payload["report_url"] == f"/api/tasks/{task_id}/report"
    assert "实验性五级风险" in payload["conclusion"]
    assert "DDPM/Pix2Pix" in payload["conclusion"]

    report = client.get(f"/api/tasks/{task_id}/report")
    assert report.status_code == 200
    assert report.mimetype == "application/pdf"
    assert report.data.startswith(b"%PDF")


def test_real_mode_model_failure_never_falls_back_to_mock(
    runtime_config, tmp_path, png_bytes
):
    missing_detector = replace(
        runtime_config.detector,
        code_dir=tmp_path / "missing-model-source",
        sam_checkpoint=tmp_path / "missing-sam.pth",
        lora_weight=tmp_path / "missing-detector.pth",
    )
    real_config = replace(
        runtime_config,
        inference_mode="real",
        detector=missing_detector,
    )
    app = create_app({"TESTING": True, "RUNTIME_CONFIG": real_config})

    try:
        client = app.test_client()
        upload = client.post(
            "/api/tasks/upload",
            data={"file": (BytesIO(png_bytes), "real-image.png")},
            content_type="multipart/form-data",
        )
        assert upload.status_code == 201
        task_id = upload.get_json()["task_id"]

        task = client.get(f"/api/tasks/{task_id}").get_json()
        assert task["status"] == "failed"
        assert "missing model asset" in task["error_message"]

        result = client.get(f"/api/tasks/{task_id}/result").get_json()
        assert result["is_mock"] is False
        assert result["model_version"] is None
        assert result["score_generated"] is None

        report = client.get(f"/api/tasks/{task_id}/report")
        assert report.status_code == 409
        assert report.get_json()["error"] == "TASK_FAILED"

        canonical_report = client.get(
            f"/api/v1/analyses/{task_id}/report"
        )
        assert canonical_report.status_code == 409
        assert canonical_report.get_json()["error"]["code"] == "TASK_FAILED"
    finally:
        app.extensions["blotguard_analysis_service"].executor.shutdown(
            wait=True
        )


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
