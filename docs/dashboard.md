
# Fleet Monitoring Dashboard

## Overview

The Fleet Monitoring Dashboard provides a visual interface for
monitoring machine failure risk using the predictive maintenance API.

## Features

- Fleet-level machine statistics
- Critical, high, medium and low risk distribution
- Machine-level failure probability
- Search by machine ID or machine name
- Filter by risk level
- Sort machines by failure probability
- Machine details and recommended maintenance actions
- Important model features with global feature importance

## Technology

- HTML
- CSS
- JavaScript
- FastAPI
- Scikit-learn
- SQLite

## API Endpoints

| Endpoint | Description |
|---|---|
| GET /api/v1/fleet/summary | Fleet-level statistics |
| GET /api/v1/fleet/predictions | Predictions for all available machines |
| GET /api/v1/predictions/{machine_id} | Individual machine prediction |
| GET /api/v1/model/status | Model status |

## Run Locally

From the project root:

```bash
uvicorn backend.app.main:app --reload
```

Open:

http://127.0.0.1:8000/dashboard

## Prediction Scope

The dashboard uses the latest available feature snapshots from
the generated historical dataset. It does not represent live
industrial telemetry.

The model's prediction horizon is 24 hours from each snapshot.
Feature importance values are global model-level importance
scores and should not be interpreted as causal explanations.
