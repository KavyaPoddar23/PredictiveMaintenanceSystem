
# Master Data Generation

## Purpose

This phase creates the synthetic reference data required by the
industrial predictive maintenance system.

## Generated entities

| Entity | Starter | Full |
|---|---:|---:|
| Plants | 1 | 3 |
| Production lines | 2 | 12 |
| Machines | 10 | 100 |
| Sensors | 50 | 500 |
| Operating shifts | 3 | 9 |
| Parts | 8 | 25 |
| Technicians | 10 | 30 |

## Hierarchy

Plant -> Production Line -> Machine -> Sensor

Each plant has four production lines in full mode.
Each machine has five sensors:

- TEMP
- VIBRATION
- PRESSURE
- RPM
- CURRENT

Each sensor has a defined unit, valid range, sampling interval,
installation date and lifecycle status.

## Deterministic IDs

Examples:

- Plant: `PLT-001`
- Production line: `LINE-PLT-001-001`
- Machine: `MCH-LINE-PLT-001-001-001`
- Sensor: `SNS-MCH-LINE-PLT-001-001-001-TEMP-01`
- Part: `PART-001`
- Technician: `TECH-001`

The generator creates parent records before child records.

## Reproducibility

Random seed: `20261022`

The generator uses Python's local `random.Random` instance.
It does not depend on the current system date or global random state.

Running the same mode with the same seed generates the same records.

## Commands

Starter dataset:

```bash
python -m scripts.generate_master_data --mode starter
```

Full dataset:

```bash
python -m scripts.generate_master_data --mode full
```

The full dataset is the required baseline for the challenge.

## Output

The generator writes CSV and JSON files to `data/master/` and inserts
the records into the SQLite database.

Generated files:

- plants.csv / plants.json
- production_lines.csv / production_lines.json
- machines.csv / machines.json
- sensors.csv / sensors.json
- operating_shifts.csv / operating_shifts.json
- parts.csv / parts.json
- technicians.csv / technicians.json

## Validation

The generator checks:

- Expected record counts
- Primary key uniqueness
- Plant-to-line foreign keys
- Line-to-machine foreign keys
- Machine-to-sensor foreign keys
- Plant-to-shift foreign keys
- Sensor type, unit and valid-range consistency
- Exactly five sensors per machine

## Data provenance

All records are synthetically generated for this challenge.
No external industrial dataset or personal data is used.
