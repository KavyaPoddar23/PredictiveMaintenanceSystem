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
| Failure