"""FastAPI integration tests for /api/runs (requires PostgreSQL)."""

from __future__ import annotations

import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL required for API integration tests",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_ok(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_run_validation_error(client: TestClient) -> None:
    r = client.post("/api/runs", json={})
    assert r.status_code == 422


def test_get_run_not_found(client: TestClient) -> None:
    rid = uuid.uuid4()
    r = client.get(f"/api/runs/{rid}")
    assert r.status_code == 404


def test_customer_ltv_not_found_run(client: TestClient) -> None:
    rid = uuid.uuid4()
    r = client.get(f"/api/runs/{rid}/customer-ltv")
    assert r.status_code == 404


def _wait_run_completed(client: TestClient, run_id: str, *, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = client.get(f"/api/runs/{run_id}")
        assert r.status_code == 200
        body = r.json()
        if body["status"] == "completed":
            return
        if body["status"] == "failed":
            pytest.fail(f"run failed: {body.get('error_message')}")
        time.sleep(0.05)
    pytest.fail("timeout waiting for run completion")


def test_create_run_full_flow_and_inference(client: TestClient) -> None:
    payload = {
        "seed": 202_503,
        "horizon_days": 12,
        "baseline_end_day": 3,
        "experiment_start_day": 6,
        "customer_count": 8,
    }
    r = client.post("/api/runs", json=payload)
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"
    run_id = data["id"]
    uuid.UUID(run_id)

    _wait_run_completed(client, run_id)

    listed = client.get("/api/runs", params={"limit": 100})
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert run_id in ids

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["parameters"]["seed"] == payload["seed"]

    daily = client.get(f"/api/runs/{run_id}/daily")
    assert daily.status_code == 200
    assert len(daily.json()) > 0

    inf = client.get(f"/api/runs/{run_id}/experiment-inference")
    assert inf.status_code == 200
    inf_body = inf.json()
    assert inf_body["run_id"] == run_id
    assert "customer_days" in inf_body["control"]


def test_experiment_inference_404_when_horizon_skips_experiment(client: TestClient) -> None:
    payload = {
        "seed": 404_001,
        "horizon_days": 5,
        "baseline_end_day": 2,
        "experiment_start_day": 10,
        "customer_count": 6,
    }
    r = client.post("/api/runs", json=payload)
    assert r.status_code == 202
    run_id = r.json()["id"]
    _wait_run_completed(client, run_id)

    inf = client.get(f"/api/runs/{run_id}/experiment-inference")
    assert inf.status_code == 404


def test_batch_creates_distinct_runs(client: TestClient) -> None:
    body = {
        "seeds": [901, 902],
        "run": {
            "seed": 900,
            "horizon_days": 6,
            "baseline_end_day": 2,
            "experiment_start_day": 4,
            "customer_count": 5,
        },
    }
    r = client.post("/api/runs/batch", json=body)
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"
    assert len(data["ids"]) == 2
    assert data["ids"][0] != data["ids"][1]

    for rid in data["ids"]:
        _wait_run_completed(client, rid)
