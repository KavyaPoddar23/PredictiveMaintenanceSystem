
## Predictive Maintenance Platform

This project generates industrial machine telemetry and maintenance
history, engineers machine-level features, trains a failure prediction
model, and exposes machine and fleet risk predictions through a REST API.

### System Components

1. Synthetic industrial data generation
2. Relational database and entity management
3. Telemetry generation and quality validation
4. Maintenance work orders and failure-event generation
5. Machine-level feature engineering
6. Random Forest failure prediction model
7. FastAPI prediction endpoints
8. Fleet monitoring dashboard
9. Automated testing and reproducibility validation

### Technology Stack

- Python
- SQLite
- SQLAlchemy
- Pandas and NumPy
- Scikit-learn
- FastAPI
- HTML, CSS and JavaScript
- Pytest

### Run the Application

Activate the virtual environment:

```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

Start the API:

```bash
uvicorn backend.app.main:app --reload
```

Dashboard:

http://127.0.0.1:8000/dashboard

API documentation:

http://127.0.0.1:8000/docs

### Run Automated Tests

```bash
python -m pytest backend/tests -v
```

### Validate Generated Data

```bash
python -m scripts.run_data_validation --mode full
```

### Verify ML Artifacts

```bash
python -m scripts.verify_ml_artifacts
```

### Reproducibility

The synthetic data generator uses the fixed seed `20261022`.

Generated data can be checked using:

```bash
python -m scripts.compare_checksums
```

### Prediction Scope and Limitations

The model is trained on synthetic historical data. Its predictions
represent the 24-hour horizon following the selected historical
feature snapshot, not the current condition of a live industrial
machine.

Feature importance values describe global model-level importance;
they are not causal explanations.

The system is a prototype and requires validation on real industrial
telemetry before operational deployment.
