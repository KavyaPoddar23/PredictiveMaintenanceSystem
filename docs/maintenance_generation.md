
# Maintenance and Failure Data Generation

## Purpose

Generate synthetic equipment failure events and their associated
maintenance history.

## Dataset configuration

- Random seed: 20261022
- Full dataset: 120 failure events
- Starter dataset: 12 failure events
- Failure types: 5
- Failure severities: LOW, MEDIUM, HIGH, CRITICAL
- Pre-failure observation window: 48 hours

## Failure types

- OVERHEATING
- EXCESSIVE_VIBRATION
- PRESSURE_DROP
- MOTOR_OVERLOAD
- BEARING_FAILURE

## Relationships

Each generated failure is linked to:

- One machine
- One corrective maintenance work order

Each work order can be linked to:

- One or more replacement parts
- One or more technicians
- Multiple status history events

The work-order-to-part and work-order-to-technician
relationships use bridge tables.

## Timeline

For each failure:

1. Symptoms begin to be observed 24 hours before failure.
2. The work order is opened two hours before the failure timestamp.
3. Maintenance starts at the failure timestamp.
4. The machine enters MAINTENANCE state.
5. Repair is completed after the generated downtime period.
6. The work order becomes COMPLETED.
7. The machine returns to RUNNING state.

## Pre-failure degradation

The generator modifies valid telemetry readings during
the 48-hour period preceding each failure.

The affected sensor values gradually change according to
the associated failure type.

Examples:

- OVERHEATING: temperature increases.
- EXCESSIVE_VIBRATION: vibration increases.
- PRESSURE_DROP: pressure decreases.
- MOTOR_OVERLOAD: current increases.
- BEARING_FAILURE: vibration increases.

Readings are kept within the configured sensor ranges.

## Work-order status history

Each work order has three recorded transitions:

- OPEN
- IN_PROGRESS
- COMPLETED

Transitions are stored as individual events rather than
overwriting the previous status history.

## Parts and inventory

Parts consumed by work orders are stored in `work_order_parts`.

Inventory is reconciled using:

Opening stock - Quantity used = Remaining stock.

The baseline opening stock is read from `data/master/parts.csv`.

## Ground-truth separation

Failure labels are written to:

`data/ground_truth/failure_labels.csv`

They are not added as columns to the telemetry input dataset.

This separation prevents direct leakage of the target label
into model input features.

## Output files

Transaction files are stored in `data/transactions/`.

Ground-truth labels are stored separately in `data/ground_truth/`.

## Reproducibility

Command:

```bash
python -m scripts.generate_maintenance --mode full
```

Seed: `20261022`

For a clean, reproducible rerun, regenerate telemetry first
using the full telemetry generator. This restores baseline
telemetry before the degradation patterns are applied again.
