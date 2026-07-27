from dataclasses import replace
from io import BytesIO

from PIL import Image
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
    return app.test_client()


@pytest.fixture()
def png_bytes():
    stream = BytesIO()
    Image.new("RGB", (320, 180), color=(230, 230, 230)).save(
        stream, format="PNG"
    )
    return stream.getvalue()
