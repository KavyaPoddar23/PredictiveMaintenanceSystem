# Industrial Predictive Maintenance System

An end-to-end industrial predictive maintenance platform that generates synthetic industrial telemetry, models equipment operating conditions, identifies machine failure risks using machine learning, and provides actionable maintenance insights through REST APIs and an interactive fleet monitoring dashboard.

The system demonstrates how industrial data engineering, relational database design, feature engineering, machine learning, backend development, and data visualization can work together in a predictive maintenance workflow.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Business Problem](#business-problem)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Dataset Overview](#dataset-overview)
- [Database Design](#database-design)
- [Data Generation Pipeline](#data-generation-pipeline)
- [Machine Learning Pipeline](#machine-learning-pipeline)
- [Backend API](#backend-api)
- [Fleet Monitoring Dashboard](#fleet-monitoring-dashboard)
- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Running the Project](#running-the-project)
- [Data Validation and Reproducibility](#data-validation-and-reproducibility)
- [Automated Testing](#automated-testing)
- [Documentation](#documentation)
- [Limitations and Future Improvements](#limitations-and-future-improvements)

---

## Project Overview

Industrial equipment failures can result in unexpected downtime, increased maintenance costs, production delays, and operational inefficiencies.

Traditional maintenance approaches often rely on fixed maintenance schedules or reactive repairs after equipment failure.

This project implements a data-driven predictive maintenance workflow that analyzes historical machine telemetry and operating conditions to estimate the likelihood of equipment failure within a 24-hour prediction horizon.

The platform includes:

- A deterministic synthetic industrial data generator.
- A relational database representing plants, production lines, machines, sensors, and maintenance operations.
- A telemetry processing and validation pipeline.
- A machine-level feature engineering workflow.
- A Random Forest classification model.
- Machine-level and fleet-level prediction APIs.
- An interactive monitoring dashboard.
- Automated tests and reproducibility checks.

**Project objective:** Transform industrial telemetry and maintenance history into structured machine-level risk predictions and actionable maintenance recommendations.

## Business Problem

Industrial facilities operate multiple machines with different operating characteristics, sensor configurations, and maintenance requirements.

Monitoring these machines manually makes it difficult to:

- Identify abnormal operating patterns.
- Detect early signs of equipment degradation.
- Prioritize machines requiring inspection.
- Understand maintenance and failure history.
- Make maintenance decisions using consistent data.

The proposed system addresses these challenges by organizing industrial data, engineering predictive features, and estimating machine failure risk.

## Key Features

### 1. Industrial Data Generation

- Generates data for multiple plants and production lines.
- Creates deterministic machine and sensor identifiers.
- Simulates temperature, vibration, pressure, and other sensor readings.
- Generates normal operating cycles, shutdown periods, and sensor anomalies.
- Simulates maintenance work orders and failure events.
- Introduces degradation patterns before selected failures.

### 2. Relational Database

- Structured industrial entity relationships.
- Primary and foreign key constraints.
- Many-to-many relationships through bridge tables.
- Machine state history.
- Work order status history.
- Maintenance and failure event tracking.

### 3. Data Quality and Validation

- Primary key uniqueness checks.
- Foreign key integrity validation.
- Duplicate telemetry detection.
- Sensor unit and range validation.
- Timestamp and maintenance lifecycle validation.
- Inventory reconciliation.
- Ground-truth separation.
- SHA-256 checksum-based reproducibility checks.

### 4. Machine Learning

- Machine-level time-window feature engineering.
- Rolling statistical features.
- Operating-state features.
- Failure-within-24-hours target labels.
- Chronological training and testing split.
- Random Forest classification.
- Model evaluation and feature importance analysis.

### 5. Predictive Maintenance API

- Individual machine failure predictions.
- Fleet-level predictions.
- Fleet risk summaries.
- Model status endpoint.
- Maintenance recommendations based on predicted risk.

### 6. Fleet Monitoring Dashboard

- Fleet-level statistics.
- Machine failure probability.
- Critical, high, medium, and low risk distribution.
- Machine search and risk filtering.
- Machine-level prediction details.
- Recommended maintenance actions.

---

## System Architecture

```text
             INDUSTRIAL DATA GENERATION
                         |
          +--------------+--------------+
          |                             |
     Master Data                  Telemetry Data
          |                             |
          +--------------+--------------+
                         |
                Maintenance Data
                         |
                         v
                SQLite Database
                         |
                         v
                Data Validation
                         |
                         v
              Feature Engineering
                         |
                         v
                Machine Features
                         |
                         v
               Failure Prediction
                 Random Forest
                         |
                         v
                Trained Model
                         |
                         v
                  FastAPI Backend
                         |
              +----------+----------+
              |                     |
              v                     v
       Machine Prediction      Fleet Prediction
              |                     |
              +----------+----------+
                         |
                         v
             Fleet Monitoring Dashboard
```

### Workflow

1. Generate industrial master data.
2. Generate telemetry for the configured operating period.
3. Generate maintenance work orders and failure events.
4. Validate the generated records and relationships.
5. Engineer machine-level features from historical telemetry.
6. Generate failure labels using documented event-based rules.
7. Train and evaluate the machine learning model.
8. Expose predictions through FastAPI.
9. Display machine and fleet risk information through the dashboard.

---

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn |
| Model | Random Forest Classifier |
| Backend | FastAPI |
| API Server | Uvicorn |
| Frontend | HTML, CSS, JavaScript |
| Testing | Pytest, HTTPX |
| Serialization | CSV, JSON, JSONL, Joblib |
| Version Control | Git, GitHub |

---

## Dataset Overview

The full synthetic dataset is configured to represent a multi-plant industrial environment.

| Entity / Dataset | Generated Records |
|---|---:|
| Plants | 3 |
| Production Lines | 12 |
| Machines | 100 |
| Sensors | 500 |
| Operating Shifts | 9 |
| Telemetry Readings | 2,160,000 |
| Maintenance Work Orders | 120 |
| Failure Events | 120 |
| Parts | 25 |
| Technicians | 30 |

### Telemetry Configuration

- Historical period: 90 days.
- Sampling interval: 30 minutes.
- Total sensors: 500.
- Readings per sensor: 4,320.
- Total readings: 2,160,000.
- Data formats: compressed CSV and compressed JSONL.
- Random seed: `20261022`.

The generated telemetry includes:

- Normal operating readings.
- Machine shutdown and operating-state changes.
- Suspected readings.
- Invalid readings.
- Spike anomalies.
- Flatline anomalies.
- Out-of-range readings.
- Degradation patterns preceding selected failures.

### Ground Truth

Failure labels are generated separately from the model input features.

The label represents whether a machine experiences a failure within the following 24-hour prediction horizon.

Ground-truth records are stored separately to avoid directly exposing failure labels and future event information to the model's input features.

---

## Database Design

The relational database models the major entities involved in industrial operations and maintenance.

### Core Entities

| Entity | Purpose |
|---|---|
| Plant | Represents an industrial facility |
| ProductionLine | Represents a production line within a plant |
| Machine | Represents industrial equipment |
| Sensor | Represents sensors installed on machines |
| TelemetryEvent | Stores timestamped sensor readings |
| OperatingShift | Represents operating shifts |
| MaintenanceWorkOrder | Tracks maintenance activities |
| FailureEvent | Records machine failure events |
| Part | Stores maintenance part information |
| Technician | Stores technician information |
| WorkOrderPart | Associates work orders with parts |
| WorkOrderTechnician | Associates work orders with technicians |
| MachineStateHistory | Records machine state transitions |
| WorkOrderStatusHistory | Records work order lifecycle transitions |

### Relationships

- One plant can contain multiple production lines.
- One production line can contain multiple machines.
- One machine can have multiple sensors.
- One sensor can produce multiple telemetry events.
- One machine can have multiple maintenance work orders.
- One machine can have multiple failure events.
- Work orders and parts have a many-to-many relationship.
- Work orders and technicians have a many-to-many relationship.

The schema uses primary keys, foreign keys, bridge tables, and historical event records to preserve data relationships and operational traceability.

Additional details are available in:

- `docs/schema.md`
- `docs/data_dictionary.md`

---

## Data Generation Pipeline

The data generation pipeline is implemented through independent Python scripts.

| Script | Responsibility |
|---|---|
| `scripts/generate_master_data.py` | Generates plants, lines, machines, sensors, shifts, parts, and technicians |
| `scripts/generate_telemetry.py` | Generates historical telemetry and machine state events |
| `scripts/generate_maintenance.py` | Generates maintenance work orders, failures, and ground-truth labels |
| `scripts/export_telemetry.py` | Exports telemetry to compressed CSV and JSONL |
| `scripts/run_data_validation.py` | Performs data integrity and domain validation |
| `scripts/compare_checksums.py` | Compares generated data checksums |

### Deterministic Generation

The generators use a fixed random seed:

```python
20261022
```

Using the same seed and generation configuration allows the synthetic dataset to be regenerated consistently.

Generate the full dataset:

```bash
python -m scripts.generate_master_data --mode full
python -m scripts.generate_telemetry --mode full
python -m scripts.generate_maintenance --mode full
python -m scripts.export_telemetry
```

Validate the generated dataset:

```bash
python -m scripts.run_data_validation --mode full
```

---

## Machine Learning Pipeline

### Feature Engineering

Machine-level features are generated using historical telemetry aggregated into six-hour time buckets.

The feature engineering process includes:

- Rolling mean.
- Rolling standard deviation.
- Minimum and maximum sensor values.
- Reading counts.
- Invalid reading rates.
- Suspected reading rates.
- Machine operating-state percentages.
- Machine criticality.

A rolling 24-hour lookback window is used to calculate historical features.

Features are shifted to ensure that information from the prediction window is not included in the model inputs.

### Target Definition

The binary classification target is:

`target_failure_within_24h`

| Target | Meaning |
|---|---|
| 0 | No failure within the next 24 hours |
| 1 | Failure occurs within the next 24 hours |

### Model

The project uses a Scikit-learn Random Forest Classifier.

The model is configured with:

- 200 estimators.
- Maximum tree depth of 12.
- Minimum samples per leaf of 3.
- Balanced subsampling of classes.
- Fixed random seed: `20261022`.

The training pipeline includes median imputation and missing-value indicators.

### Model Evaluation

The model evaluation workflow uses a chronological train/test split to preserve temporal ordering.

Evaluation metrics include:

- Accuracy.
- Precision.
- Recall.
- F1-score.
- ROC-AUC.
- PR-AUC.
- Confusion matrix.

The generated evaluation report is saved at:

`backend/app/ml/artifacts/evaluation_report.json`

Feature importance:

`backend/app/ml/artifacts/feature_importance.csv`

Trained model:

`backend/app/ml/artifacts/failure_prediction_model.joblib`

The model artifact stores the trained pipeline, feature column names, prediction horizon, and random seed.

### Generate Features and Train the Model

```bash
python -m scripts.build_ml_dataset
python -m scripts.train_failure_model
```

Verify the generated ML artifacts:

```bash
python -m scripts.verify_ml_artifacts
```

---

## Backend API

The backend is developed using FastAPI.

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/api/v1/model/status` | Model status |
| GET | `/api/v1/predictions/{machine_id}` | Individual machine prediction |
| GET | `/api/v1/fleet/predictions` | Predictions for all available machines |
| GET | `/api/v1/fleet/summary` | Fleet-level risk summary |

### Individual Machine Prediction

Example:

```http
GET /api/v1/predictions/{machine_id}
```

The response includes:

- Machine identifier.
- Machine name and type.
- Machine criticality.
- Snapshot timestamp.
- Prediction timestamp.
- Failure probability.
- Risk classification.
- Recommended maintenance action.
- Model version.
- Important model features.

### Risk Classification

The platform classifies predicted failure probabilities using the following thresholds:

| Probability | Risk Level |
|---|---|
| 0.00–0.24 | LOW |
| 0.25–0.49 | MEDIUM |
| 0.50–0.74 | HIGH |
| 0.75–1.00 | CRITICAL |

### Recommended Actions

| Risk Level | Recommended Action |
|---|---|
| LOW | Continue routine monitoring |
| MEDIUM | Schedule an inspection |
| HIGH | Prioritize maintenance inspection |
| CRITICAL | Arrange immediate inspection |

These thresholds are configurable application rules, not independently calibrated industrial failure probabilities.

---

## Fleet Monitoring Dashboard

The frontend provides a centralized interface for monitoring the generated machine predictions.

### Dashboard Features

- Total machine count.
- High-risk machine count.
- Average predicted failure probability.
- Critical machine count.
- Risk distribution.
- Search by machine ID or name.
- Filter machines by risk level.
- Sort predictions by failure probability.
- View individual machine details.
- View recommended maintenance actions.
- Inspect important model features.

### Access the Dashboard

After starting the backend, open:

`http://127.0.0.1:8000/dashboard`

API documentation:

`http://127.0.0.1:8000/docs`

---

## Project Structure

```text
PredictiveMaintenanceSystem/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── predictions.py
│   │   │
│   │   ├── models/
│   │   │   └── entities.py
│   │   │
│   │   ├── schemas/
│   │   │   └── prediction.py
│   │   │
│   │   ├── services/
│   │   │   └── prediction_service.py
│   │   │
│   │   ├── ml/
│   │   │   └── artifacts/
│   │   │       ├── failure_prediction_model.joblib
│   │   │       ├── evaluation_report.json
│   │   │       └── feature_importance.csv
│   │   │
│   │   ├── database.py
│   │   └── main.py
│   │
│   └── tests/
│       ├── test_api.py
│       └── test_database.py
│
├── data/
│   ├── master/
│   ├── telemetry/
│   ├── transactions/
│   ├── ground_truth/
│   ├── features/
│   ├── validation_reports/
│   └── industrial_maintenance.db
│
├── docs/
│   ├── schema.md
│   ├── data_dictionary.md
│   ├── telemetry_generation.md
│   ├── maintenance_generation.md
│   ├── data_validation.md
│   ├── ml_pipeline.md
│   └── prediction_api.md
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── scripts/
│   ├── init_db.py
│   ├── verify_schema.py
│   ├── generate_master_data.py
│   ├── verify_master_data.py
│   ├── generate_telemetry.py
│   ├── verify_telemetry.py
│   ├── generate_maintenance.py
│   ├── verify_maintenance.py
│   ├── export_telemetry.py
│   ├── run_data_validation.py
│   ├── compare_checksums.py
│   ├── build_ml_dataset.py
│   ├── train_failure_model.py
│   └── verify_ml_artifacts.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

*The structure above summarizes the principal project files; generated data and supporting scripts may include additional files.*

---

## Installation and Setup

### Prerequisites

- Python 3.10 or later.
- Git.
- Visual Studio Code or another Python IDE.
- PowerShell or a terminal.

### 1. Clone the Repository

```bash
git clone https://github.com/KavyaPoddar23/PredictiveMaintenanceSystem.git

cd PredictiveMaintenanceSystem
```

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If dependencies have not been installed, the main packages include:

```bash
pip install fastapi uvicorn sqlalchemy pandas numpy scikit-learn joblib pytest httpx
```

### 4. Initialize the Database

```bash
python -m scripts.init_db
```

### 5. Generate the Dataset

Run the generators in the correct order:

```bash
python -m scripts.generate_master_data --mode full

python -m scripts.generate_telemetry --mode full

python -m scripts.generate_maintenance --mode full

python -m scripts.export_telemetry
```

### 6. Validate the Dataset

```bash
python -m scripts.run_data_validation --mode full
```

### 7. Build the ML Dataset

```bash
python -m scripts.build_ml_dataset
```

### 8. Train the Model

```bash
python -m scripts.train_failure_model
```

### 9. Verify ML Artifacts

```bash
python -m scripts.verify_ml_artifacts
```

### 10. Start the Application

```bash
uvicorn backend.app.main:app --reload
```

---

## Running the Project

Once the application is running, access the following interfaces:

| Interface | URL |
|---|---|
| Fleet Dashboard | http://127.0.0.1:8000/dashboard |
| API Documentation | http://127.0.0.1:8000/docs |
| Health Check | http://127.0.0.1:8000/health |
| Fleet Summary | http://127.0.0.1:8000/api/v1/fleet/summary |
| Fleet Predictions | http://127.0.0.1:8000/api/v1/fleet/predictions |
| Model Status | http://127.0.0.1:8000/api/v1/model/status |

---

## Data Validation and Reproducibility

Data quality and traceability are important parts of the project.

The validation workflow checks:

- Required entity record counts.
- Primary key uniqueness.
- Foreign key integrity.
- Telemetry duplicates.
- Sensor reading coverage.
- Sensor units and valid ranges.
- Telemetry quality statuses.
- Maintenance timeline consistency.
- Machine and work order relationships.
- Inventory reconciliation.
- Ground-truth separation.
- Required generated output files.

### Run Validation

```bash
python -m scripts.run_data_validation --mode full
```

### Reproducibility Checks

The generator uses the fixed seed `20261022`.

The checksum comparison workflow compares generated output files against a saved baseline.

```bash
python -m scripts.compare_checksums
```

Validation reports are stored in:

```text
data/validation_reports/
├── validation_summary.json
├── validation_details.csv
├── checksums.json
└── checksums_baseline.json
```

A successful checksum comparison indicates that the compared generated files match the saved baseline.

---

## Automated Testing

The project uses Pytest for automated testing.

Test coverage includes:

- API health endpoint.
- Root endpoint.
- Model status endpoint.
- Individual machine prediction response.
- Invalid machine handling.
- Fleet prediction endpoint.
- Fleet summary endpoint.
- Database table existence.
- Primary key uniqueness.
- Foreign key integrity.
- Master data record counts.
- Telemetry coverage.
- Orphaned telemetry detection.
- Failure record relationships.
- Maintenance date consistency.

### Run Tests

```bash
python -m pytest backend/tests -v
```

---

## Documentation

Additional technical documentation is available in the `docs/` directory.

| Document | Description |
|---|---|
| `schema.md` | Database architecture and entity relationships |
| `data_dictionary.md` | Entity and field definitions |
| `telemetry_generation.md` | Telemetry simulation approach |
| `maintenance_generation.md` | Maintenance and failure generation |
| `data_validation.md` | Data quality and validation rules |
| `ml_pipeline.md` | Feature engineering and model training |
| `prediction_api.md` | API endpoints and prediction responses |
| `dashboard.md` | Fleet dashboard documentation |

---

## Limitations and Future Improvements

### Current Limitations

- The dataset is synthetically generated and does not represent measurements collected from an actual industrial facility.
- Predictions are based on the latest available historical feature snapshots in the generated dataset.
- The 24-hour prediction horizon is relative to the feature snapshot, not necessarily the current real-world time.
- Risk thresholds are application-defined and have not been calibrated against real operational costs.
- Global feature importance provides model-level insights, not causal explanations for individual machine failures.
- The current application does not ingest live sensor streams.

### Future Improvements

- Integrate real-time telemetry ingestion using MQTT or Apache Kafka.
- Support live machine monitoring and scheduled predictions.
- Introduce time-series forecasting and advanced anomaly detection.
- Evaluate XGBoost, LightGBM, and sequence-based models.
- Add model explainability using SHAP.
- Implement model monitoring and drift detection.
- Integrate maintenance scheduling and technician assignment.
- Add role-based authentication and access control.
- Deploy the application using Docker and cloud infrastructure.
- Calibrate risk thresholds using real-world maintenance costs and failure data.

---

## Project Outcome

The project demonstrates an end-to-end predictive maintenance workflow, from synthetic industrial data generation and relational data modeling to machine learning, backend APIs, and fleet-level monitoring.

It brings together data engineering, machine learning, backend development, validation, and visualization in a single industrial use case.

**Repository:** https://github.com/KavyaPoddar23/PredictiveMaintenanceSystem

---

## Author

**Kavya Poddar**

- GitHub: [https://github.com/KavyaPoddar23](https://github.com/KavyaPoddar23)
- LinkedIn: [https://www.linkedin.com/in/kavyapoddar](https://www.linkedin.com/in/kavyapoddar)

