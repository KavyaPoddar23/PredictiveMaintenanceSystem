
# Database Schema and Relationships

## Database

SQLite relational database.

File: data/industrial_maintenance.db

## Entity Hierarchy

Plant
  └── ProductionLine
       └── Machine
            ├── Sensor
            │    └── TelemetryEvent
            ├── MaintenanceWorkOrder
            │    ├── WorkOrderPart
            │    │    └── Part
            │    ├── WorkOrderTechnician
            │    │    └── Technician
            │    ├── FailureEvent (optional 1:1)
            │    └── WorkOrderStatusHistory
            ├── FailureEvent
            └── MachineStateHistory

Plant
  └── OperatingShift

## Primary Keys

Every core entity has a deterministic string primary key.

Bridge tables use composite primary keys.

## Foreign Keys

- production_lines.plant_id -> plants.plant_id
- machines.line_id -> production_lines.line_id
- sensors.machine_id -> machines.machine_id
- telemetry_events.sensor_id -> sensors.sensor_id
- operating_shifts.plant_id -> plants.plant_id
- maintenance_work_orders.machine_id -> machines.machine_id
- failure_events.machine_id -> machines.machine_id
- failure_events.work_order_id -> maintenance_work_orders.work_order_id
- work_order_parts.work_order_id -> maintenance_work_orders.work_order_id
- work_order_parts.part_id -> parts.part_id
- work_order_technicians.work_order_id -> maintenance_work_orders.work_order_id
- work_order_technicians.technician_id -> technicians.technician_id
- machine_state_history.machine_id -> machines.machine_id
- work_order_status_history.work_order_id -> maintenance_work_orders.work_order_id
- work_order_status_history.changed_by -> technicians.technician_id

## Cardinality

- Plant to ProductionLine: 1:N
- ProductionLine to Machine: 1:N
- Machine to Sensor: 1:N
- Sensor to TelemetryEvent: 1:N
- Plant to OperatingShift: 1:N
- Machine to MaintenanceWorkOrder: 1:N
- Machine to FailureEvent: 1:N
- MaintenanceWorkOrder to FailureEvent: 1:0..1
- MaintenanceWorkOrder to Part: N:M
- MaintenanceWorkOrder to Technician: N:M

## Lifecycle States

### Machine Lifecycle

ACTIVE
INACTIVE
UNDER_MAINTENANCE
RETIRED

### Machine Operating States

RUNNING
IDLE
SHUTDOWN
MAINTENANCE

### Work Order States

OPEN
PLANNED
IN_PROGRESS
COMPLETED
CANCELLED

### Sensor States

ACTIVE
INACTIVE
FAULTY
REMOVED

## Effective Dates

Production lines, operating shifts and sensors retain their
effective installation or operational dates.

Records are not silently overwritten when an asset changes state.

## History Preservation

MachineStateHistory records machine operating-state changes.

WorkOrderStatusHistory records maintenance work-order status
changes.

Both tables retain timestamps and previous/new states.

## Data Separation

Validated operational records are stored in relational tables.

Deliberately invalid test cases are isolated in a separate
anomaly/quarantine dataset.

Failure ground-truth labels are kept separately from
predictive model input features.
