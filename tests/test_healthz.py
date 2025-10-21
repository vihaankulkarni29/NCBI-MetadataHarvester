from fastapi.testclient import TestClient
from src.ncbi_metadata_harvester.main import app


def test_healthz():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
