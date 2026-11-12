
# Phase 7: Predictive Maintenance ML Pipeline

## Objective

Predict whether an industrial machine will experience a failure within
the next 24 hours using its historical telemetry and operating context.

## Dataset configuration

- Random seed: 20261022
- Machines: 100
- Telemetry duration: 90 days
- Telemetry sampling interval: 30 minutes
- Feature snapshot interval: 6 hours
- Feature lookback window: 24 hours
- Prediction horizon: 24 hours

## Feature engineering

Telemetry is aggregated into six-hour buckets at machine and sensor-type
level.

The previous four buckets are used to calculate:

- Rolling mean
- Rolling standard deviation
- Rolling minimum
- Rolling maximum
- Reading count
- Invalid reading rate
- Suspect reading rate
- Operating-state percentages

Machine criticality is included as a static numeric feature.

Missing feature values are retained as missing values and imputed during
model training. They are not replaced with zero.

## Label definition

For a snapshot at time t:

- Positive (1): at least one failure occurs in (t, t + 24 hours].
- Negative (0): no failure occurs in that interval.

Snapshots are created every six hours.

The feature window uses only telemetry recorded before the snapshot time.
Failure event timestamps are used only to construct labels.

## Data separation

Feature file:

`data/features/machine_features.csv`

Label file:

`data/features/machine_labels.csv`

Metadata:

`data/features/feature_metadata.json`

The ground-truth failure records are never used as model input features.

## Model

Algorithm: Random Forest Classifier

Configuration:

- 200 estimators
- Maximum depth: 12
- Minimum samples per leaf: 3
- Class weighting: balanced_subsample
- Random seed: 20261022

Missing numeric values are handled using median imputation.

## Evaluation

A chronological 70/30 split is used.

A 24-hour gap separates training snapshots from the test period because
the prediction horizon is 24 hours.

Metrics:

- Accuracy
- Precision
- Recall
- F1 score
- ROC-AUC
- PR-AUC
- Confusion matrix

The default classification threshold is 0.5.

## Artifacts

- `backend/app/ml/artifacts/failure_prediction_model.joblib`
- `backend/app/ml/artifacts/evaluation_report.json`
- `backend/app/ml/artifacts/feature_importance.csv`

## Commands

Generate features and labels:

```powershell
python -m scripts.build_ml_dataset
```

Train and evaluate:

```powershell
python -m scripts.train_failure_model
```

## Limitations

This is a synthetic baseline dataset and a baseline classifier.

Model performance on synthetic data does not establish real-world
industrial failure prediction performance.

A production system would require validated real equipment data,
calibration, drift monitoring, operational alert thresholds, and
human review of maintenance recommendations.
