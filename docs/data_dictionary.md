
# Industrial Predictive Maintenance System
# Data Dictionary

## 1. General Conventions

- Database: SQLite
- Primary keys: Immutable string identifiers
- Foreign keys: Must reference existing parent records
- Timestamps: Stored as UTC-naive datetime values
- Display timezone: Configured per plant
- Units: Explicitly stored with sensor configuration and telemetry
- Missing values: NULL where permitted, never silently replaced by zero
- History: State changes are appended as new records

## 2. Plant

Table: plants

| Field | Type | Required | Rules |
|---|---|---|---|
| plant_id | VARCHAR(50) | Yes | PK, unique, PLT-001 format |
| name | VARCHAR(150) | Yes | Non-empty |
| location | VARCHAR(200) | Yes | Non-empty |
| timezone | VARCHAR(80) | Yes | Valid timezone name |
| status | VARCHAR(20) | Yes | ACTIVE, INACTIVE |
| created_at | DATETIME | Yes | Creation timestamp |

## 3. ProductionLine

Table: production_lines

| Field | Type | Required | Rules |
|---|---|---|---|
| line_id | VARCHAR(100) | Yes | PK, LINE-{plant-id}-001 |
| plant_id | VARCHAR(50) | Yes | FK -> plants |
| name | VARCHAR(150) | Yes | Non-empty |
| status | VARCHAR(20) | Yes | ACTIVE, INACTIVE, MAINTENANCE |
| effective_from | DATE | Yes | Valid start date |
| effective_to | DATE | No | Must be >= effective_from |

Unique: plant_id + name

## 4. Machine

Table: machines

| Field | Type | Required | Rules |
|---|---|---|---|
| machine_id | VARCHAR(150) | Yes | PK, MCH-{line-id}-001 |
| line_id | VARCHAR(100) | Yes | FK -> production_lines |
| name | VARCHAR(150) | Yes | Non-empty |
| machine_type | VARCHAR(100) | Yes | Defined machine category |
| manufacturer | VARCHAR(150) | No | Manufacturer name |
| model | VARCHAR(100) | No | Model identifier |
| install_date | DATE | Yes | Valid installation date |
| criticality | VARCHAR(20) | Yes | LOW, MEDIUM, HIGH, CRITICAL |
| lifecycle_state | VARCHAR(30) | Yes | ACTIVE, INACTIVE, UNDER_MAINTENANCE, RETIRED |
| operating_state | VARCHAR(30) | Yes | RUNNING, IDLE, SHUTDOWN, MAINTENANCE |
| created_at | DATETIME | Yes | Creation timestamp |

## 5. Sensor

Table: sensors

| Field | Type | Required | Rules |
|---|---|---|---|
| sensor_id | VARCHAR(200) | Yes | PK, SNS-{machine-id}-{type}-01 |
| machine_id | VARCHAR(150) | Yes | FK -> machines |
| sensor_type | VARCHAR(50) | Yes | TEMP, VIBRATION, PRESSURE, RPM, CURRENT |
| unit | VARCHAR(30) | Yes | degC, mm/s, bar, rpm, A |
| min_valid | FLOAT | Yes | Must be less than max_valid |
| max_valid | FLOAT | Yes | Must be greater than min_valid |
| sampling_interval_seconds | INTEGER | Yes | Positive number |
| status | VARCHAR(20) | Yes | ACTIVE, INACTIVE, FAULTY, REMOVED |
| installed_at | DATETIME | Yes | Installation timestamp |
| removed_at | DATETIME | No | Must be >= installed_at |

## 6. TelemetryEvent

Table: telemetry_events

| Field | Type | Required | Rules |
|---|---|---|---|
| telemetry_id | VARCHAR(300) | Yes | PK, TEL-{sensor-id}-{timestamp} |
| sensor_id | VARCHAR(200) | Yes | FK -> sensors |
| event_timestamp | DATETIME | Yes | UTC timestamp |
| value | FLOAT | Yes | Numeric measurement |
| unit | VARCHAR(30) | Yes | Must match sensor unit |
| operating_state | VARCHAR(30) | Yes | RUNNING, IDLE, SHUTDOWN, MAINTENANCE |
| quality_status | VARCHAR(20) | Yes | VALID, SUSPECT, INVALID |
| issue_type | VARCHAR(100) | No | Explicit anomaly category |

Unique: sensor_id + event_timestamp

Sensor ranges are validated against the corresponding sensor's
min_valid and max_valid configuration.

## 7. OperatingShift

Table: operating_shifts

| Field | Type | Required | Rules |
|---|---|---|---|
| shift_id | VARCHAR(150) | Yes | PK, deterministic ID |
| plant_id | VARCHAR(50) | Yes | FK -> plants |
| shift_name | VARCHAR(50) | Yes | DAY, EVENING, NIGHT |
| starts_at | TIME | Yes | Valid local shift time |
| ends_at | TIME | Yes | Valid local shift time |
| effective_from | DATE | Yes | Valid start date |
| effective_to | DATE | No | Must be >= effective_from |
| status | VARCHAR(20) | Yes | ACTIVE, INACTIVE |

Unique: plant_id + shift_name + effective_from

## 8. MaintenanceWorkOrder

Table: maintenance_work_orders

| Field | Type | Required | Rules |
|---|---|---|---|
| work_order_id | VARCHAR(100) | Yes | PK, WO-2026-000001 |
| machine_id | VARCHAR(150) | Yes | FK -> machines |
| maintenance_type | VARCHAR(50) | Yes | PREVENTIVE, CORRECTIVE, PREDICTIVE |
| priority | VARCHAR(20) | Yes | LOW, MEDIUM, HIGH, CRITICAL |
| status | VARCHAR(30) | Yes | OPEN, PLANNED, IN_PROGRESS, COMPLETED, CANCELLED |
| reason | TEXT | Yes | Non-empty |
| opened_at | DATETIME | Yes | Opening timestamp |
| planned_start | DATETIME | No | Planned maintenance timestamp |
| actual_start | DATETIME | No | >= opened_at |
| actual_end | DATETIME | No | >= actual_start |
| notes | TEXT | No | Maintenance notes |

## 9. FailureEvent

Table: failure_events

| Field | Type | Required | Rules |
|---|---|---|---|
| failure_event_id | VARCHAR(100) | Yes | PK, deterministic ID |
| machine_id | VARCHAR(150) | Yes | FK -> machines |
| work_order_id | VARCHAR(100) | No | Unique FK -> maintenance_work_orders |
| failure_type | VARCHAR(100) | Yes | Defined failure category |
| severity | VARCHAR(20) | Yes | LOW, MEDIUM, HIGH, CRITICAL |
| symptom_first_observed_at | DATETIME | No | First recorded symptom |
| occurred_at | DATETIME | Yes | Actual failure time |
| downtime_start | DATETIME | Yes | Downtime start |
| downtime_end | DATETIME | No | >= downtime_start |
| root_cause | TEXT | No | Documented failure cause |

Failure labels will be maintained separately in ground_truth
and must not be exposed as predictive model input features.

## 10. Part

Table: parts

| Field | Type | Required | Rules |
|---|---|---|---|
| part_id | VARCHAR(100) | Yes | PK, PRT-000001 |
| name | VARCHAR(150) | Yes | Non-empty |
| part_type | VARCHAR(100) | Yes | Defined part category |
| unit_cost | FLOAT | Yes | >= 0 |
| stock_quantity | INTEGER | Yes | >= 0 |
| status | VARCHAR(30) | Yes | AVAILABLE, LOW_STOCK, OUT_OF_STOCK, DISCONTINUED |

Currency: INR for generated cost values.

## 11. Technician

Table: technicians

| Field | Type | Required | Rules |
|---|---|---|---|
| technician_id | VARCHAR(100) | Yes | PK, TECH-000001 |
| name | VARCHAR(150) | Yes | Non-empty synthetic name |
| skill_specialty | VARCHAR(100) | Yes | Defined technical specialty |
| employment_status | VARCHAR(20) | Yes | ACTIVE, INACTIVE |

## 12. Bridge Tables

### WorkOrderPart

- work_order_id: FK -> maintenance_work_orders
- part_id: FK -> parts
- quantity: positive INTEGER
- unit_cost_at_use: FLOAT >= 0
- used_at: DATETIME

Composite PK: work_order_id + part_id

### WorkOrderTechnician

- work_order_id: FK -> maintenance_work_orders
- technician_id: FK -> technicians
- assigned_at: DATETIME
- released_at: Optional DATETIME >= assigned_at
- role: VARCHAR(100)

Composite PK: work_order_id + technician_id

## 13. Event History Tables

### MachineStateHistory

- state_event_id: PK
- machine_id: FK -> machines
- previous_state: Optional VARCHAR(30)
- new_state: VARCHAR(30)
- changed_at: DATETIME
- reason: TEXT

### WorkOrderStatusHistory

- status_event_id: PK
- work_order_id: FK -> maintenance_work_orders
- previous_status: Optional VARCHAR(30)
- new_status: VARCHAR(30)
- changed_at: DATETIME
- changed_by: Optional FK -> technicians

History records are append-only.

## 14. Relationship Cardinality

| Parent | Child | Cardinality |
|---|---|---|
| Plant | ProductionLine | 1:N |
| ProductionLine | Machine | 1:N |
| Machine | Sensor | 1:N |
| Sensor | TelemetryEvent | 1:N |
| Plant | OperatingShift | 1:N |
| Machine | MaintenanceWorkOrder | 1:N |
| Machine | FailureEvent | 1:N |
| MaintenanceWorkOrder | FailureEvent | 1:0..1 |
| MaintenanceWorkOrder | Part | N:M |
| MaintenanceWorkOrder | Technician | N:M |
| Machine | MachineStateHistory | 1:N |
| MaintenanceWorkOrder | WorkOrderStatusHistory | 1:N |

## 15. Data Integrity Rules

1. Every primary key must be unique.
2. Every foreign key must reference a valid parent.
3. Sensor units must match telemetry units.
4. Sensor values must be checked against configured ranges.
5. Duplicate sensor timestamps are prohibited.
6. Maintenance dates must be chronologically valid.
7. Machine state transitions must follow allowed lifecycle rules.
8. Failure events must reference valid machines.
9. Replacement part quantities must be positive.
10. Technician assignment dates must be valid.
11. Derived downtime must be calculated from source timestamps.
12. Failure labels must remain separate from model features.

## 16. Data Generation Configuration

Random seed: 20261022

Target configuration:
- Plants: 3
- Production lines: 12
- Machines: 100
- Sensors: 500
- Telemetry period: 90 days
- Telemetry records: 1,000,000 to 3,000,000
- Labelled failures: 100 to 200

The same generator must support both starter and full datasets.
