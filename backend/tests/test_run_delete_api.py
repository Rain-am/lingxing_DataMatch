from fastapi.testclient import TestClient

from app import main


def test_delete_run_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(main, "delete_run", lambda run_id: False)
    client = TestClient(main.app)

    response = client.delete("/api/reconcile/runs/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "run not found"
