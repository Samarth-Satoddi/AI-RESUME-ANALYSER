def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "service" in data


def test_readiness_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["subsystems"]["storage"] == "ready"


def test_api_v1_root(client):
    response = client.get("/api/v1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["ai_provider"] == "heuristic"
