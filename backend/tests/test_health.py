from backend.blotguard import create_app


def test_health_endpoint():
    client = create_app({"TESTING": True}).test_client()

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "blotguard-api"}
