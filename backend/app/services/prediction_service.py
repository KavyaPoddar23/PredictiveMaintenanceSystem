
import sqlite3
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[3]

DB_PATH = ROOT / "data" / "industrial_maintenance.db"

FEATURES_PATH = (
    ROOT / "data" / "features" / "machine_features.csv"
)

MODEL_PATH = (
    ROOT
    / "backend"
    / "app"
    / "ml"
    / "artifacts"
    / "failure_prediction_model.joblib"
)

IMPORTANCE_PATH = (
    ROOT
    / "backend"
    / "app"
    / "ml"
    / "artifacts"
    / "feature_importance.csv"
)

MODEL_VERSION = "rf-v1"
PREDICTION_HORIZON_HOURS = 24


@lru_cache(maxsize=1)
def load_model_bundle():
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Trained model not found. "
                "Run Phase 7 model training first."
            ),
        )

    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to load trained model: {str(exc)}",
        )


@lru_cache(maxsize=1)
def load_feature_dataset():
    if not FEATURES_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Feature dataset not found. "
                "Run Phase 7 feature generation first."
            ),
        )

    try:
        return pd.read_csv(FEATURES_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to read feature dataset: {str(exc)}",
        )


@lru_cache(maxsize=1)
def load_feature_importance():
    if not IMPORTANCE_PATH.exists():
        return {}

    try:
        importance_df = pd.read_csv(IMPORTANCE_PATH)

        return dict(
            zip(
                importance_df["feature"],
                importance_df["importance"],
            )
        )
    except Exception:
        return {}


def get_machine_details(machine_id):
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Machine database is unavailable.",
        )

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        row = connection.execute(
            """
            SELECT *
            FROM machines
            WHERE machine_id = ?
            """,
            (machine_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Machine {machine_id} not found.",
            )

        details = dict(row)

        return {
            "machine_id": details.get("machine_id"),
            "machine_name": details.get("name"),
            "machine_type": details.get("machine_type")
            or details.get("type"),
            "criticality": details.get("criticality"),
        }

    finally:
        connection.close()


def get_risk_level(probability):
    if probability >= 0.75:
        return "CRITICAL"

    if probability >= 0.50:
        return "HIGH"

    if probability >= 0.25:
        return "MEDIUM"

    return "LOW"


def get_recommended_action(risk_level):
    recommendations = {
        "CRITICAL": (
            "Prioritize immediate inspection. "
            "Review recent telemetry and consider controlled shutdown "
            "according to plant safety procedures."
        ),
        "HIGH": (
            "Schedule an urgent machine inspection and review "
            "recent sensor readings."
        ),
        "MEDIUM": (
            "Increase monitoring frequency and review unusual "
            "telemetry patterns."
        ),
        "LOW": (
            "Continue normal monitoring and follow the "
            "preventive maintenance schedule."
        ),
    }

    return recommendations[risk_level]


def get_important_features(feature_values, feature_columns, limit=5):
    importance_map = load_feature_importance()

    if not importance_map:
        return []

    candidates = []

    for feature in feature_columns:
        importance = importance_map.get(feature)

        if importance is None:
            continue

        value = feature_values.get(feature)

        if pd.isna(value):
            observed_value = None
        else:
            observed_value = float(value)

        candidates.append({
            "feature": feature,
            "observed_value": observed_value,
            "global_importance": float(importance),
        })

    candidates.sort(
        key=lambda item: item["global_importance"],
        reverse=True,
    )

    return candidates[:limit]


def predict_machine_failure(machine_id):
    bundle = load_model_bundle()

    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    feature_dataset = load_feature_dataset()

    if "machine_id" not in feature_dataset.columns:
        raise HTTPException(
            status_code=500,
            detail="Feature dataset has no machine_id column.",
        )

    machine_rows = feature_dataset[
        feature_dataset["machine_id"] == machine_id
    ].copy()

    if machine_rows.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No feature snapshots found for machine {machine_id}."
            ),
        )

    machine_rows["snapshot_timestamp"] = pd.to_datetime(
        machine_rows["snapshot_timestamp"],
        errors="coerce",
    )

    machine_rows = machine_rows.dropna(
        subset=["snapshot_timestamp"]
    )

    if machine_rows.empty:
        raise HTTPException(
            status_code=422,
            detail="No valid snapshot timestamps found.",
        )

    latest_row = machine_rows.sort_values(
        "snapshot_timestamp"
    ).iloc[-1]

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in latest_row.index
    ]

    if missing_features:
        raise HTTPException(
            status_code=500,
            detail=(
                "Feature dataset does not match the trained model. "
                f"Missing features: {missing_features}"
            ),
        )

    input_frame = pd.DataFrame(
        [
            {
                feature: latest_row[feature]
                for feature in feature_columns
            }
        ]
    )

    try:
        probability = float(
            model.predict_proba(input_frame)[0][1]
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(exc)}",
        )

    risk_level = get_risk_level(probability)

    feature_values = {
        feature: latest_row[feature]
        for feature in feature_columns
    }

    important_features = get_important_features(
        feature_values,
        feature_columns,
    )

    machine_details = get_machine_details(machine_id)

    return {
        **machine_details,
        "snapshot_timestamp": (
            latest_row["snapshot_timestamp"].isoformat()
            if hasattr(latest_row["snapshot_timestamp"], "isoformat")
            else str(latest_row["snapshot_timestamp"])
        ),
        "prediction_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "prediction_horizon_hours": (
            PREDICTION_HORIZON_HOURS
        ),
        "failure_probability": round(probability, 6),
        "risk_level": risk_level,
        "recommended_action": get_recommended_action(
            risk_level
        ),
        "model_version": MODEL_VERSION,
        "important_features": important_features,
        "explanation_note": (
            "Feature importance values represent global model "
            "importance, not causal or individual prediction effects. "
            "The prediction uses the latest available generated "
            "feature snapshot, not live streaming telemetry."
        ),
    }


def get_model_status():
    bundle = load_model_bundle()

    return {
        "model_loaded": True,
        "model_version": MODEL_VERSION,
        "prediction_horizon_hours": (
            PREDICTION_HORIZON_HOURS
        ),
        "feature_count": len(bundle["feature_columns"]),
        "model_type": type(
            bundle["model"].named_steps["classifier"]
        ).__name__,
        "message": "Prediction model is ready.",
    }


def get_fleet_predictions():
    """
    Generate the latest available prediction for every machine
    represented in the ML feature dataset.
    """
    features = load_feature_dataset()

    machine_ids = sorted(
        features["machine_id"].dropna().unique().tolist()
    )

    predictions = []

    for machine_id in machine_ids:
        try:
            prediction = predict_machine_failure(str(machine_id))
            predictions.append(prediction)
        except Exception as exc:
            print(f"Prediction failed for {machine_id}: {exc}")

    return predictions


def get_fleet_summary():
    """
    Return aggregate risk statistics for the machine fleet.
    """
    predictions = get_fleet_predictions()

    risk_counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }

    for prediction in predictions:
        risk_level = prediction["risk_level"]

        if risk_level in risk_counts:
            risk_counts[risk_level] += 1

    total_machines = len(predictions)

    high_risk_machines = (
        risk_counts["CRITICAL"] + risk_counts["HIGH"]
    )

    average_probability = (
        sum(p["failure_probability"] for p in predictions)
        / total_machines
        if total_machines else 0
    )

    return {
        "total_machines": total_machines,
        "high_risk_machines": high_risk_machines,
        "average_failure_probability": round(
            average_probability, 4
        ),
        "risk_distribution": risk_counts,
        "predictions": predictions
    }
