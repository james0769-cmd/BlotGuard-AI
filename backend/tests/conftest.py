from dataclasses import replace
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter
import pytest

from backend.blotguard import create_app
from backend.blotguard.core.config import load_runtime_config


@pytest.fixture()
def runtime_config(tmp_path):
    base = load_runtime_config()
    return replace(
        base,
        storage_root=tmp_path / "tasks",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        execution_mode="inline",
        inference_mode="mock",
        allowed_origins=("http://localhost:4200",),
    )


@pytest.fixture()
def app(runtime_config):
    app = create_app(
        {
            "TESTING": True,
            "RUNTIME_CONFIG": runtime_config,
        }
    )
    yield app
    app.extensions["blotguard_analysis_service"].executor.shutdown(wait=True)


@pytest.fixture()
def client(app):
    client = app.test_client()
    session = client.post(
        "/api/auth/register",
        json={"username": "test_user", "password": "password123"},
    ).get_json()
    client.environ_base["HTTP_AUTHORIZATION"] = f'Bearer {session["access_token"]}'
    return client


@pytest.fixture()
def png_bytes():
    stream = BytesIO()
    image = Image.new("RGB", (320, 180), color=(230, 230, 230))
    draw = ImageDraw.Draw(image)
    for y in (45, 90, 135):
        draw.rounded_rectangle((35, y, 135, y + 14), radius=6, fill=(45, 45, 45))
        draw.rounded_rectangle((180, y, 285, y + 14), radius=6, fill=(60, 60, 60))
    image.filter(ImageFilter.GaussianBlur(radius=3)).save(stream, format="PNG")
    return stream.getvalue()
