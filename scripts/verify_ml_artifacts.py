
from pathlib import Path
import json
import pandas as pd
import joblib


ROOT = Path(__file__).resolve().parents[1]

FEATURES_PATH = ROOT / "data" / "features" / "machine_features.csv"
LABELS_PATH = ROOT / "data" / "features" / "machine_labels.csv"
METADATA_PATH = ROOT / "data" / "features" / "feature_metadata.json"

MODEL_PATH = (
    ROOT / "backend" / "app" / "ml" / "artifacts"
    / "failure_prediction_model.joblib"
)

REPORT_PATH = (
    ROOT / "backend" / "app" / "ml" / "artifacts"
    / "evaluation_report.json"
)

IMPORTANCE_PATH = (
    ROOT / "backend" / "app" / "ml" / "artifacts"
    / "feature_importance.csv"
)

TARGET_COLUMN = "target_failure_within_24h"


def main():
    required_files = [
        FEATURES_PATH,
        LABELS_PATH,
        METADATA_PATH,
        MODEL_PATH,
        REPORT_PATH,
        IMPORTANCE_PATH
    ]

    missing = [
        str(path) for path in required_files
        if not path.exists()
    ]

    if missing:
        raise SystemExit(
            "Missing ML artifacts:\n" + "\n".join(missing)
        )

    features = pd.read_csv(FEATURES_PATH)
    labels = pd.read_csv(LABELS_PATH)

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    with open(REPORT_PATH, "r", encoding="utf-8") as file:
        evaluation = json.load(file)

    bundle = joblib.load(MODEL_PATH)
    importance = pd.read_csv(IMPORTANCE_PATH)

    if not isinstance(bundle, dict):
        raise SystemExit("Model artifact must be a dictionary bundle.")

    required_bundle_keys = {
        "model",
        "feature_columns",
        "prediction_horizon_hours",
        "random_seed"
    }

    missing_keys = required_bundle_keys - set(bundle.keys())

    if missing_keys:
        raise SystemExit(
            f"Missing model bundle keys: {missing_keys}"
        )

    model = bundle["model"]
    saved_feature_columns = bundle["feature_columns"]

    if not hasattr(model, "predict_proba"):
        raise SystemExit(
            "The trained model pipeline does not support predict_proba."
        )

    if not features.columns.is_unique:
        raise SystemExit("Duplicate feature column names found.")

    if features.empty or labels.empty:
        raise SystemExit("Feature or label dataset is empty.")

    required_columns = {
        "snapshot_id",
        "machine_id",
        "snapshot_timestamp"
    }

    if not required_columns.issubset(features.columns):
        raise SystemExit(
            "Required columns missing from feature dataset."
        )

    if not required_columns.issubset(labels.columns):
        raise SystemExit(
            "Required columns missing from label dataset."
        )

    if TARGET_COLUMN not in labels.columns:
        raise SystemExit(
            f"Target column '{TARGET_COLUMN}' missing from labels."
        )

    if features["snapshot_id"].duplicated().any():
        raise SystemExit("Duplicate snapshot IDs in features.")

    if labels["snapshot_id"].duplicated().any():
        raise SystemExit("Duplicate snapshot IDs in labels.")

    if set(features["snapshot_id"]) != set(labels["snapshot_id"]):
        raise SystemExit(
            "Feature and label snapshot IDs do not match."
        )

    if labels[TARGET_COLUMN].isna().any():
        raise SystemExit("Missing target labels found.")

    target_values = set(labels[TARGET_COLUMN].unique())

    if not target_values.issubset({0, 1}):
        raise SystemExit(
            f"Invalid target values found: {target_values}"
        )

    if len(target_values) != 2:
        raise SystemExit(
            "Target dataset must contain both positive and negative labels."
        )

    excluded_columns = {
        "snapshot_id",
        "machine_id",
        "snapshot_timestamp"
    }

    feature_columns = [
        column for column in features.columns
        if column not in excluded_columns
    ]

    forbidden_terms = [
        "failure",
        "work_order",
        "ground_truth",
        "downtime",
        "root_cause",
        "symptom",
        "occurred_at",
        "label",
        "target"
    ]

    suspicious_columns = [
        column for column in feature_columns
        if any(term in column.lower() for term in forbidden_terms)
    ]

    if suspicious_columns:
        raise SystemExit(
            f"Potential target leakage: {suspicious_columns}"
        )

    if not isinstance(saved_feature_columns, list):
        raise SystemExit(
            "Model feature_columns must be a list."
        )

    if feature_columns != saved_feature_columns:
        raise SystemExit(
            "Saved model feature columns do not match "
            "the current feature dataset."
        )

    if not importance.empty:
        if "feature" not in importance.columns:
            raise SystemExit(
                "Feature importance file is missing its feature column."
            )

    if not isinstance(bundle["prediction_horizon_hours"], int):
        raise SystemExit("Invalid prediction horizon.")

    if bundle["prediction_horizon_hours"] != 24:
        raise SystemExit(
            "Expected a 24-hour prediction horizon."
        )

    if not isinstance(bundle["random_seed"], int):
        raise SystemExit("Invalid model random seed.")

    if not isinstance(metadata, dict):
        raise SystemExit("Invalid feature metadata format.")

    if not isinstance(evaluation, dict):
        raise SystemExit("Invalid evaluation report format.")

    print("\nML ARTIFACT VERIFICATION")
    print("=" * 45)

    print(f"Feature rows: {len(features)}")
    print(f"Label rows: {len(labels)}")
    print(f"Feature columns: {len(feature_columns)}")
    print(f"Unique machines: {features['machine_id'].nunique()}")

    print(
        f"Positive labels: {(labels[TARGET_COLUMN] == 1).sum()}"
    )

    print(
        f"Negative labels: {(labels[TARGET_COLUMN] == 0).sum()}"
    )

    print(f"Target column: {TARGET_COLUMN}")
    print(f"Model type: {type(model).__name__}")
    print(f"Prediction horizon: {bundle['prediction_horizon_hours']} hours")
    print(f"Random seed: {bundle['random_seed']}")
    print(f"Feature importance rows: {len(importance)}")

    print("\nML ARTIFACT VERIFICATION PASSED")


if __name__ == "__main__":
    main()
