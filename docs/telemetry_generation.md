
# Telemetry Generation

## Purpose

Generate synthetic sensor telemetry for 90 days across the
industrial equipment hierarchy.

## Dataset configuration

- Random seed: 20261022
- Start timestamp: 2026-01-01 00:00:00
- Duration: 90 days
- Sampling interval: 1800 seconds
- Number of sensors: 500
- Expected telemetry readings: 2,160,000

## Calculation

500 sensors x 48 readings per day x 90 days
= 2,160,000 readings.

## Sensor types and units

| Sensor | Unit |
|---|---|
| Temperature | degC |
| Vibration | mm/s |
| Pressure | bar |
| RPM | rpm |
| Current | A |

## Operating states

- RUNNING
- IDLE
- SHUTDOWN

Weekday operating schedules produce running and idle cycles.
Weekend schedules produce shutdown periods.
A small group of machines operates during night hours.

Every operating-state transition is recorded in
`machine_state_history`.

## Telemetry quality

| Quality status | Meaning |
|---|---|
| VALID | Reading follows the normal generated pattern |
| SUSPECT | Reading may indicate a sensor problem |
| INVALID | Reading violates the configured sensor range |

Fault patterns include:

- SPIKE
- FLATLINE
- OUT_OF_RANGE

Faults are associated with individual sensor windows and are
generated deterministically using the configured seed.

## Output files

Location: `data/telemetry/`

- `telemetry_events.csv.gz`
- `telemetry_events.jsonl.gz`
- `machine_state_history.csv`
- `machine_state_history.jsonl`

The compressed JSONL file contains one JSON object per line.
This format supports streaming large datasets without loading
the entire dataset into memory.

## Database

Telemetry readings are stored in the `telemetry_events` table.
Machine state transitions are stored in `machine_state_history`.

The generator replaces previously generated telemetry and
state-history records before inserting a new run.

## Reproducibility

Command:

```bash
python -m scripts.generate_telemetry --mode full
```

The generator uses seed `20261022` and fixed timestamps.
The same code, master data and seed produce the same records.

## Important separation

This phase does not generate failure labels.
Failure events and ground-truth labels are maintained separately
from model input features in later phases.

## Validation

Run:

```bash
python -m scripts.verify_telemetry
```

The validation checks record counts, sensor coverage, data quality,
timestamp coverage, foreign-key integrity and output files.
