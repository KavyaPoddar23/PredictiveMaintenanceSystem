
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.app.main import app
import backend.app.api.predictions as prediction_api


client = TestClient(app)


SAMPLE_PREDICTION = {
    "machine_id": "MCH-LINE-PLT-001-001-001",
    "machine_name": "Test Machine",
    "machine_type": "PUMP",
    "criticality": "HIGH",
    "snapshot_timestamp": "2026-03-31T18:00:00",
    "prediction_timestamp": "2026-11-12T10:00:00",
    "prediction_horizon_hours": 24,
    "failure_probability": 0.82,
    "risk_level": "CRITICAL",
    "recommended_action": "Schedule immediate inspection.",
    "model_version": "rf-v1",
    "important_features": [
        {
            "feature": "TEMP_rolling_mean",
            "observed_value": 85.5,
            "global_importance": 0.25
        }
    ],
    "explanation_note": "Test explanation."
}


SAMPLE_MODEL_STATUS = {
    "model_loaded": True,
    "model_version": "rf-v1",
    "prediction_horizon_hours": 24,
    "feature_count": 20,
    "model_type": "RandomForestClassifier",
    "message": "Model loaded successfully."
}


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["dashboard"] == "/dashboard"


def test_model_status_endpoint(monkeypatch):
    monkeypatch.setattr(
        prediction_api,
        "get_model_status",
        lambda: SAMPLE_MODEL_STATUS
    )

    response = client.get("/api/v1/model/status")

    assert response.status_code == 200
    assert response.json()["model_loaded"] is True
    assert response.json()["model_version"] == "rf-v1"


def test_single_machine_prediction(monkeypatch):
    monkeypatch.setattr(
        prediction_api,
        "predict_machine_failure",
        lambda machine_id: SAMPLE_PREDICTION
    )

    response = client.get(
        "/api/v1/predictions/MCH-LINE-PLT-001-001-001"
    )

    assert response.status_code == 200

    result = response.json()

    assert result["machine_id"] == SAMPLE_PREDICTION["machine_id"]
    assert result["failure_probability"] == 0.82
    assert result["risk_level"] == "CRITICAL"


def test_prediction_not_found(monkeypatch):
    def raise_not_found(machine_id):
        raise HTTPException(
            status_code=404,
            detail="Machine not found."
        )

    monkeypatch.setattr(
        prediction_api,
        "predict_machine_failure",
        raise_not_found
    )

    response = client.get(
        "/api/v1/predictions/INVALID-MACHINE"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found."


def test_fleet_predictions_endpoint(monkeypatch):
    monkeypatch.setattr(
        prediction_api,
        "get_fleet_predictions",
        lambda: [SAMPLE_PREDICTION]
    )

    response = client.get("/api/v1/fleet/predictions")

    assert response.status_code == 200
    assert response.json()["total_machines"] == 1
    assert len(response.json()["predictions"]) == 1


def test_fleet_summary_endpoint(monkeypatch):
    sample_summary = {
        "total_machines": 1,
        "high_risk_machines": 1,
        "average_failure_probability": 0.82,
        "risk_distribution": {
            "CRITICAL": 1,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        },
        "predictions": [SAMPLE_PREDICTION]
    }

    monkeypatch.setattr(
        prediction_api,
        "get_fleet_summary",
        lambda: sample_summary
    )

    response = client.get("/api/v1/fleet/summary")

    assert response.status_code == 200

    result = response.json()

    assert result["total_machines"] == 1
    assert result["high_risk_machines"] == 1
    assert result["risk_distribution"]["CRITICAL"] == 1
