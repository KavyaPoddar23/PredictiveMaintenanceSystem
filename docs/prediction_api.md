
# Phase 8: Prediction API

## Overview

The prediction API serves failure-risk predictions from the trained
Random Forest model.

It uses the latest available feature snapshot for the requested
machine.

The current implementation uses the generated synthetic feature
dataset. It does not consume live streaming telemetry.

## Model

- Algorithm: Random Forest Classifier
- Model version: rf-v1
- Prediction horizon: 24 hours
- Input: Machine-level telemetry and operating-context features
- Output: Failure probability and risk category

## Endpoints

### GET /

Returns API information.

### GET /health

Returns service health.

### GET /api/v1/model/status

Returns model availability, type, version and feature count.

### GET /api/v1/predictions/{machine_id}

Returns the latest available failure-risk prediction for a machine.

Example:

`GET /api/v1/predictions/MCH-LINE-PLT-001-001`

## Risk classification

The initial demonstration thresholds are:

| Probability | Risk |
|---|---|
| Below 0.25 | LOW |
| 0.25 to below 0.50 | MEDIUM |
| 0.50 to below 0.75 | HIGH |
| 0.75 and above | CRITICAL |

These are configurable demonstration thresholds, not calibrated
industrial safety thresholds.

## Prediction response

The response includes:

- Machine ID and available machine metadata
- Feature snapshot timestamp
- Prediction timestamp
- Prediction horizon
- Failure probability
- Risk classification
- Recommended action
- Model version
- Globally important model features and their observed values

Feature importance is a global model-level explanation. It does
not prove that an individual feature caused a particular prediction.

## Error handling

- HTTP 404: Machine or feature snapshot not found
- HTTP 422: Invalid feature snapshot
- HTTP 500: Prediction or data-processing error
- HTTP 503: Model or required dataset unavailable

## Run the API

From the project root:

```powershell
uvicorn backend.app.main:app --reload
```

Swagger documentation:

`http://127.0.0.1:8000/docs`

Health endpoint:

`http://127.0.0.1:8000/health`
