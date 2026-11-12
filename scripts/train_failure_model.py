
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]

FEATURES_PATH = ROOT / "data" / "features" / "machine_features.csv"
LABELS_PATH = ROOT / "data" / "features" / "machine_labels.csv"

ARTIFACT_DIR = ROOT / "backend" / "app" / "ml" / "artifacts"

MODEL_PATH = ARTIFACT_DIR / "failure_prediction_model.joblib"
REPORT_PATH = ARTIFACT_DIR / "evaluation_report.json"
IMPORTANCE_PATH = ARTIFACT_DIR / "feature_importance.csv"

RANDOM_SEED = 20261022
PREDICTION_HOURS = 24


def load_dataset():
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            "Feature file missing. Run "
            "python -m scripts.build_ml_dataset first."
        )

    if not LABELS_PATH.exists():
        raise FileNotFoundError(
            "Label file missing. Run "
            "python -m scripts.build_ml_dataset first."
        )

    features = pd.read_csv(FEATURES_PATH)
    labels = pd.read_csv(LABELS_PATH)

    required_feature_columns = {
        "snapshot_id",
        "machine_id",
        "snapshot_timestamp",
    }

    required_label_columns = {
        "snapshot_id",
        "target_failure_within_24h",
    }

    if not required_feature_columns.issubset(features.columns):
        raise ValueError("Feature file is missing required columns.")

    if not required_label_columns.issubset(labels.columns):
        raise ValueError("Label file is missing required columns.")

    if features["snapshot_id"].duplicated().any():
        raise ValueError("Duplicate snapshot IDs in feature file.")

    if labels["snapshot_id"].duplicated().any():
        raise ValueError("Duplicate snapshot IDs in label file.")

    dataset = features.merge(
        labels[["snapshot_id", "target_failure_within_24h"]],
        on="snapshot_id",
        how="inner",
        validate="one_to_one",
    )

    if len(dataset) != len(features) or len(dataset) != len(labels):
        raise ValueError(
            "Feature and label snapshots do not match exactly."
        )

    dataset["snapshot_timestamp"] = pd.to_datetime(
        dataset["snapshot_timestamp"],
        errors="raise",
    )

    dataset["target_failure_within_24h"] = (
        dataset["target_failure_within_24h"].astype(int)
    )

    if not set(
        dataset["target_failure_within_24h"].unique()
    ).issubset({0, 1}):
        raise ValueError("Target must contain only 0 and 1.")

    return dataset


def select_feature_columns(dataset):
    excluded_columns = {
        "snapshot_id",
        "machine_id",
        "snapshot_timestamp",
        "target_failure_within_24h",
    }

    feature_columns = [
        column
        for column in dataset.columns
        if column not in excluded_columns
    ]

    if not feature_columns:
        raise ValueError("No model input features found.")

    # Only numeric sensor and operating-context features are used.
    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(
            dataset[column]
        )
    ]

    if non_numeric:
        raise ValueError(
            f"Non-numeric feature columns found: {non_numeric}"
        )

    # Explicitly prevent accidental leakage.
    forbidden_terms = [
        "failure",
        "work_order",
        "ground_truth",
        "downtime",
        "root_cause",
        "symptom",
        "occurred_at",
        "label",
        "target",
    ]

    suspicious_columns = [
        column
        for column in feature_columns
        if any(
            term in column.lower()
            for term in forbidden_terms
        )
    ]

    if suspicious_columns:
        raise ValueError(
            "Potential target leakage in feature columns: "
            f"{suspicious_columns}"
        )

    return feature_columns


def chronological_split(dataset):
    timestamps = sorted(
        dataset["snapshot_timestamp"].unique()
    )

    if len(timestamps) < 10:
        raise ValueError(
            "Not enough distinct timestamps for a time-based split."
        )

    cutoff_index = int(len(timestamps) * 0.70)
    cutoff_time = pd.Timestamp(timestamps[cutoff_index])

    # A training label must finish before the test period begins.
    training_end = cutoff_time - pd.Timedelta(
        hours=PREDICTION_HOURS
    )

    train_mask = (
        dataset["snapshot_timestamp"] < training_end
    )

    test_mask = (
        dataset["snapshot_timestamp"] >= cutoff_time
    )

    train_data = dataset.loc[train_mask].copy()
    test_data = dataset.loc[test_mask].copy()

    if train_data.empty or test_data.empty:
        raise ValueError(
            "Chronological split produced an empty dataset."
        )

    if train_data["target_failure_within_24h"].nunique() < 2:
        raise ValueError(
            "Training data contains only one target class. "
            "Check failure event distribution."
        )

    if test_data["target_failure_within_24h"].nunique() < 2:
        raise ValueError(
            "Test data contains only one target class. "
            "A meaningful classification evaluation is not possible."
        )

    return train_data, test_data, cutoff_time, training_end


def calculate_metrics(y_true, probabilities):
    predictions = (probabilities >= 0.5).astype(int)

    matrix = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    )

    tn, fp, fn, tp = matrix.ravel()

    return {
        "accuracy": float(
            accuracy_score(y_true, predictions)
        ),
        "precision": float(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "f1_score": float(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "roc_auc": float(
            roc_auc_score(y_true, probabilities)
        ),
        "pr_auc": float(
            average_precision_score(
                y_true,
                probabilities,
            )
        ),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "classification_threshold": 0.5,
    }


def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading feature and label datasets...")
    dataset = load_dataset()

    feature_columns = select_feature_columns(dataset)

    print(f"Total snapshots: {len(dataset):,}")
    print(f"Input features: {len(feature_columns)}")
    print(
        "Positive samples:",
        int(dataset["target_failure_within_24h"].sum()),
    )

    train_data, test_data, cutoff_time, training_end = (
        chronological_split(dataset)
    )

    X_train = train_data[feature_columns]
    y_train = train_data["target_failure_within_24h"]

    X_test = test_data[feature_columns]
    y_test = test_data["target_failure_within_24h"]

    print("\nChronological split")
    print("-------------------")
    print(f"Training rows: {len(train_data):,}")
    print(f"Test rows: {len(test_data):,}")
    print(f"Training ends before: {training_end}")
    print(f"Test starts at: {cutoff_time}")

    print("\nTraining Random Forest classifier...")

    model = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=12,
                    min_samples_leaf=3,
                    class_weight="balanced_subsample",
                    random_state=RANDOM_SEED,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]

    metrics = calculate_metrics(
        y_test,
        probabilities,
    )

    classifier = model.named_steps["classifier"]

    # Median imputation with add_indicator=True can append columns.
    # Preserve the original feature importances' transformed names.
    imputer = model.named_steps["imputer"]

    transformed_names = imputer.get_feature_names_out(
        feature_columns
    )

    importance = pd.DataFrame({
        "feature": transformed_names,
        "importance": classifier.feature_importances_,
    }).sort_values(
        "importance",
        ascending=False,
    )

    importance.to_csv(
        IMPORTANCE_PATH,
        index=False,
    )

    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "prediction_horizon_hours": PREDICTION_HOURS,
            "random_seed": RANDOM_SEED,
        },
        MODEL_PATH,
    )

    report = {
        "model": "RandomForestClassifier",
        "prediction_target": (
            "Failure within the next 24 hours"
        ),
        "prediction_horizon_hours": PREDICTION_HOURS,
        "lookback_hours": 24,
        "snapshot_interval_hours": 6,
        "random_seed": RANDOM_SEED,
        "split_strategy": "Chronological 70/30 with 24-hour gap",
        "cutoff_time": cutoff_time.isoformat(),
        "training_end_before": training_end.isoformat(),
        "training_rows": len(train_data),
        "test_rows": len(test_data),
        "training_positive_samples": int(y_train.sum()),
        "test_positive_samples": int(y_test.sum()),
        "feature_count": len(feature_columns),
        "input_features": feature_columns,
        "metrics": metrics,
        "artifacts": {
            "model": str(MODEL_PATH.relative_to(ROOT)),
            "feature_importance": str(
                IMPORTANCE_PATH.relative_to(ROOT)
            ),
        },
    }

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(report, file, indent=4)

    print("\n" + "=" * 55)
    print("MODEL EVALUATION")
    print("=" * 55)

    for name, value in metrics.items():
        print(f"{name}: {value}")

    print("\nModel saved:", MODEL_PATH)
    print("Evaluation saved:", REPORT_PATH)
    print("Feature importance saved:", IMPORTANCE_PATH)

    print("\nPhase 7 model training completed.")


if __name__ == "__main__":
    main()
