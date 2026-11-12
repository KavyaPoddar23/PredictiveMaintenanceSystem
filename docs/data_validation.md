
# Data Validation and Reproducibility

## Overview

Phase 6 validates the synthetic industrial predictive maintenance dataset.

The validation process checks:

- Database table availability
- Expected record counts
- Primary key uniqueness
- Foreign key integrity
- Parent-child relationships
- Telemetry completeness
- Sensor units and measurement ranges
- Telemetry quality classifications
- Maintenance work order timelines
- Failure and work order relationships
- Machine state history events
- Parts inventory reconciliation
- Ground truth label availability
- Generated output files

## Dataset Configuration

- Random seed: 20261022
- Plants: 3
- Production lines: 12
- Machines: 100
- Sensors: 500
- Operating shifts: 9
- Telemetry readings: 2,160,000
- Maintenance work orders: 120
- Failure events: 120
- Parts: 25
- Technicians: 30
- Telemetry duration: 90 days
- Sampling interval: 30 minutes

## Run Validation

From the project root:

```powershell
python -m scripts.export_telemetry
python -m scripts.run_data_validation --mode full
```

## Validation Reports

Generated reports:

- `data/validation_reports/validation_summary.json`
- `data/validation_reports/validation_details.csv`
- `data/validation_reports/checksums.json`

## Reproducibility

The dataset is generated using a fixed random seed.

SHA-256 checksums are calculated for generated files.

To compare two complete dataset generations:

1. Generate and validate the first dataset.
2. Save its checksum file as the baseline.
3. Regenerate the complete dataset using the same seed.
4. Export telemetry and validate again.
5. Compare the current checksums with the baseline.

The SQLite database file is excluded from checksum comparisons because database file-level metadata can differ even when the generated records are equivalent.

## Reproducibility Commands

```powershell
Copy-Item data\validation_reports\checksums.json data\validation_reports\checksums_baseline.json

python -m scripts.generate_master_data --mode full
python -m scripts.generate_telemetry --mode full
python -m scripts.generate_maintenance --mode full
python -m scripts.export_telemetry
python -m scripts.run_data_validation --mode full
python -m scripts.compare_checksums
```

## Ground Truth Separation

Failure labels are stored separately from telemetry input data.

Ground truth is used for supervised learning and evaluation. It must not be included as an input feature during model training or inference.
