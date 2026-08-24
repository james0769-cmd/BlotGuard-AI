from datetime import datetime, timedelta, timezone
from io import BytesIO

from sqlalchemy import func, select

from backend.blotguard import create_app
from backend.blotguard.persistence.models import AnalysisItem, Artifact


def test_real_registration_login_and_token_validation(client):
    missing = client.post(
        "/api/auth/login",
        json={"username": "missing", "password": "password123"},
    )
    assert missing.status_code == 401
    assert missing.get_json()["error"] == "INVALID_CREDENTIALS"

    weak = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "123"},
    )
    assert weak.status_code == 400
    assert weak.get_json()["error"] == "WEAK_PASSWORD"

    registered = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password123"},
    )
    assert registered.status_code == 201
    registration = registered.get_json()
    assert registration["access_token"] != "mock-access-token"
    assert registration["token_type"] == "Bearer"
    assert registration["expires_in"] > 0
    assert registration["user"]["username"] == "alice"

    duplicate = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password123"},
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"] == "USERNAME_TAKEN"

    wrong_password = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.get_json()["error"] == "INVALID_CREDENTIALS"

    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    unauthenticated = client.get("/api/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.get_json()["error"] == "AUTHENTICATION_REQUIRED"

    invalid = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-valid"}
    )
    assert invalid.status_code == 401
    assert invalid.get_json()["error"] == "INVALID_TOKEN"

    current = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert current.status_code == 200
    assert current.get_json()["user"]["username"] == "alice"


def test_registered_user_persists_across_app_restart(runtime_config):
    first = create_app({"TESTING": True, "RUNTIME_CONFIG": runtime_config})
    try:
        response = first.test_client().post(
            "/api/auth/register",
            json={"username": "persistent", "password": "password123"},
        )
        assert response.status_code == 201
    finally:
        first.extensions["blotguard_analysis_service"].executor.shutdown(
            wait=True
        )

    second = create_app({"TESTING": True, "RUNTIME_CONFIG": runtime_config})
    try:
        response = second.test_client().post(
            "/api/auth/login",
            json={"username": "persistent", "password": "password123"},
        )
        assert response.status_code == 200
    finally:
        second.extensions["blotguard_analysis_service"].executor.shutdown(
            wait=True
        )


def test_compat_delete_removes_database_rows_and_task_files(
    app, client, png_bytes
):
    uploaded = client.post(
        "/api/tasks/upload",
        data={"file": (BytesIO(png_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    task_id = uploaded.get_json()["task_id"]

    listed = client.get("/api/tasks?limit=20")
    assert listed.status_code == 200
    listed_ids = [task["task_id"] for task in listed.get_json()["tasks"]]
    assert task_id in listed_ids

    storage = app.extensions["blotguard_storage"]
    repository = app.extensions["blotguard_repository"]
    task_dir = storage.task_dir(task_id)
    assert task_dir.exists()

    deleted = client.delete(f"/api/tasks/{task_id}")
    assert deleted.status_code == 204
    assert not task_dir.exists()
    assert client.get(f"/api/tasks/{task_id}").status_code == 404
    listed_after_delete = client.get("/api/tasks?limit=20").get_json()
    assert task_id not in {
        task["task_id"] for task in listed_after_delete["tasks"]
    }

    with repository.sessions() as session:
        item_count = session.scalar(
            select(func.count()).select_from(AnalysisItem).where(
                AnalysisItem.task_id == task_id
            )
        )
        artifact_count = session.scalar(
            select(func.count()).select_from(Artifact).where(
                Artifact.task_id == task_id
            )
        )
    assert item_count == 0
    assert artifact_count == 0


def test_cleanup_deletes_only_expired_terminal_tasks(
    app, client, png_bytes
):
    old = client.post(
        "/api/tasks/upload",
        data={"file": (BytesIO(png_bytes), "old.png")},
        content_type="multipart/form-data",
    ).get_json()["task_id"]
    recent = client.post(
        "/api/tasks/upload",
        data={"file": (BytesIO(png_bytes), "recent.png")},
        content_type="multipart/form-data",
    ).get_json()["task_id"]

    repository = app.extensions["blotguard_repository"]
    service = app.extensions["blotguard_analysis_service"]
    storage = app.extensions["blotguard_storage"]
    with repository.sessions.begin() as session:
        from backend.blotguard.persistence.models import AnalysisTask

        task = session.get(AnalysisTask, old)
        task.completed_at = datetime.now(timezone.utc) - timedelta(days=40)

    result = service.cleanup_expired(older_than_days=30)

    assert result["deleted"] == [old]
    assert result["failed"] == {}
    assert not storage.task_dir(old).exists()
    assert client.get(f"/api/tasks/{old}").status_code == 404
    assert client.get(f"/api/tasks/{recent}").status_code == 200
