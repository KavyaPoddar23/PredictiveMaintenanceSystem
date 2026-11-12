
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Date,
    DateTime,
    Time,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func
)

from sqlalchemy.orm import relationship

from backend.app.database import Base


# ==========================================================
# 1. PLANT
# ==========================================================

class Plant(Base):
    __tablename__ = "plants"

    plant_id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    location = Column(String(200), nullable=False)
    timezone = Column(String(80), nullable=False, default="Asia/Kolkata")
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_plant_status"
        ),
    )

    production_lines = relationship(
        "ProductionLine",
        back_populates="plant"
    )

    operating_shifts = relationship(
        "OperatingShift",
        back_populates="plant"
    )


# ==========================================================
# 2. PRODUCTION LINE
# ==========================================================

class ProductionLine(Base):
    __tablename__ = "production_lines"

    line_id = Column(String(100), primary_key=True)

    plant_id = Column(
        String(50),
        ForeignKey("plants.plant_id"),
        nullable=False
    )

    name = Column(String(150), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")

    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "plant_id",
            "name",
            name="uq_line_plant_name"
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE')",
            name="ck_line_status"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_line_effective_dates"
        ),
    )

    plant = relationship(
        "Plant",
        back_populates="production_lines"
    )

    machines = relationship(
        "Machine",
        back_populates="production_line"
    )


# ==========================================================
# 3. MACHINE
# ==========================================================

class Machine(Base):
    __tablename__ = "machines"

    machine_id = Column(String(150), primary_key=True)

    line_id = Column(
        String(100),
        ForeignKey("production_lines.line_id"),
        nullable=False
    )

    name = Column(String(150), nullable=False)
    machine_type = Column(String(100), nullable=False)

    manufacturer = Column(String(150), nullable=True)
    model = Column(String(100), nullable=True)

    install_date = Column(Date, nullable=False)

    criticality = Column(String(20), nullable=False, default="MEDIUM")

    lifecycle_state = Column(
        String(30),
        nullable=False,
        default="ACTIVE"
    )

    operating_state = Column(
        String(30),
        nullable=False,
        default="SHUTDOWN"
    )

    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_machine_criticality"
        ),
        CheckConstraint(
            "lifecycle_state IN "
            "('ACTIVE', 'INACTIVE', 'UNDER_MAINTENANCE', 'RETIRED')",
            name="ck_machine_lifecycle"
        ),
        CheckConstraint(
            "operating_state IN "
            "('RUNNING', 'IDLE', 'SHUTDOWN', 'MAINTENANCE')",
            name="ck_machine_operating_state"
        ),
    )

    production_line = relationship(
        "ProductionLine",
        back_populates="machines"
    )

    sensors = relationship(
        "Sensor",
        back_populates="machine"
    )

    maintenance_work_orders = relationship(
        "MaintenanceWorkOrder",
        back_populates="machine"
    )

    failure_events = relationship(
        "FailureEvent",
        back_populates="machine"
    )

    state_history = relationship(
        "MachineStateHistory",
        back_populates="machine"
    )


# ==========================================================
# 4. SENSOR
# ==========================================================

class Sensor(Base):
    __tablename__ = "sensors"

    sensor_id = Column(String(200), primary_key=True)

    machine_id = Column(
        String(150),
        ForeignKey("machines.machine_id"),
        nullable=False
    )

    sensor_type = Column(String(50), nullable=False)
    unit = Column(String(30), nullable=False)

    min_valid = Column(Float, nullable=False)
    max_valid = Column(Float, nullable=False)

    sampling_interval_seconds = Column(
        Integer,
        nullable=False,
        default=60
    )

    status = Column(String(20), nullable=False, default="ACTIVE")

    installed_at = Column(DateTime, nullable=False)
    removed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "min_valid < max_valid",
            name="ck_sensor_valid_range"
        ),
        CheckConstraint(
            "sampling_interval_seconds > 0",
            name="ck_sensor_sampling_interval"
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'FAULTY', 'REMOVED')",
            name="ck_sensor_status"
        ),
        CheckConstraint(
            "removed_at IS NULL OR removed_at >= installed_at",
            name="ck_sensor_installation_dates"
        ),
    )

    machine = relationship(
        "Machine",
        back_populates="sensors"
    )

    telemetry_events = relationship(
        "TelemetryEvent",
        back_populates="sensor"
    )


# ==========================================================
# 5. TELEMETRY EVENT
# ==========================================================

class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    telemetry_id = Column(String(300), primary_key=True)

    sensor_id = Column(
        String(200),
        ForeignKey("sensors.sensor_id"),
        nullable=False
    )

    event_timestamp = Column(DateTime, nullable=False)

    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=False)

    operating_state = Column(String(30), nullable=False)

    quality_status = Column(
        String(20),
        nullable=False,
        default="VALID"
    )

    issue_type = Column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "event_timestamp",
            name="uq_sensor_timestamp"
        ),
        CheckConstraint(
            "operating_state IN "
            "('RUNNING', 'IDLE', 'SHUTDOWN', 'MAINTENANCE')",
            name="ck_telemetry_operating_state"
        ),
        CheckConstraint(
            "quality_status IN "
            "('VALID', 'SUSPECT', 'INVALID')",
            name="ck_telemetry_quality"
        ),
        Index(
            "idx_telemetry_sensor_timestamp",
            "sensor_id",
            "event_timestamp"
        ),
    )

    sensor = relationship(
        "Sensor",
        back_populates="telemetry_events"
    )


# ==========================================================
# 6. OPERATING SHIFT
# ==========================================================

class OperatingShift(Base):
    __tablename__ = "operating_shifts"

    shift_id = Column(String(150), primary_key=True)

    plant_id = Column(
        String(50),
        ForeignKey("plants.plant_id"),
        nullable=False
    )

    shift_name = Column(String(50), nullable=False)

    starts_at = Column(Time, nullable=False)
    ends_at = Column(Time, nullable=False)

    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    status = Column(String(20), nullable=False, default="ACTIVE")

    __table_args__ = (
        UniqueConstraint(
            "plant_id",
            "shift_name",
            "effective_from",
            name="uq_shift_plant_effective"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_shift_effective_dates"
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_shift_status"
        ),
    )

    plant = relationship(
        "Plant",
        back_populates="operating_shifts"
    )


# ==========================================================
# 7. MAINTENANCE WORK ORDER
# ==========================================================

class MaintenanceWorkOrder(Base):
    __tablename__ = "maintenance_work_orders"

    work_order_id = Column(String(100), primary_key=True)

    machine_id = Column(
        String(150),
        ForeignKey("machines.machine_id"),
        nullable=False
    )

    maintenance_type = Column(String(50), nullable=False)

    priority = Column(String(20), nullable=False)

    status = Column(String(30), nullable=False, default="OPEN")

    reason = Column(Text, nullable=False)

    opened_at = Column(DateTime, nullable=False)

    planned_start = Column(DateTime, nullable=True)

    actual_start = Column(DateTime, nullable=True)

    actual_end = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_work_order_priority"
        ),
        CheckConstraint(
            "status IN "
            "('OPEN', 'PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_work_order_status"
        ),
        CheckConstraint(
            "actual_start IS NULL OR actual_start >= opened_at",
            name="ck_work_order_start"
        ),
        CheckConstraint(
            "actual_end IS NULL OR "
            "(actual_start IS NOT NULL AND actual_end >= actual_start)",
            name="ck_work_order_end"
        ),
    )

    machine = relationship(
        "Machine",
        back_populates="maintenance_work_orders"
    )

    parts_used = relationship(
        "WorkOrderPart",
        back_populates="work_order"
    )

    technician_assignments = relationship(
        "WorkOrderTechnician",
        back_populates="work_order"
    )

    status_history = relationship(
        "WorkOrderStatusHistory",
        back_populates="work_order"
    )

    failure_event = relationship(
        "FailureEvent",
        back_populates="work_order",
        uselist=False
    )


# ==========================================================
# 8. FAILURE EVENT
# ==========================================================

class FailureEvent(Base):
    __tablename__ = "failure_events"

    failure_event_id = Column(String(100), primary_key=True)

    machine_id = Column(
        String(150),
        ForeignKey("machines.machine_id"),
        nullable=False
    )

    work_order_id = Column(
        String(100),
        ForeignKey("maintenance_work_orders.work_order_id"),
        nullable=True,
        unique=True
    )

    failure_type = Column(String(100), nullable=False)

    severity = Column(String(20), nullable=False)

    symptom_first_observed_at = Column(DateTime, nullable=True)

    occurred_at = Column(DateTime, nullable=False)

    downtime_start = Column(DateTime, nullable=False)

    downtime_end = Column(DateTime, nullable=True)

    root_cause = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_failure_severity"
        ),
        CheckConstraint(
            "downtime_end IS NULL OR downtime_end >= downtime_start",
            name="ck_failure_downtime"
        ),
    )

    machine = relationship(
        "Machine",
        back_populates="failure_events"
    )

    work_order = relationship(
        "MaintenanceWorkOrder",
        back_populates="failure_event"
    )


# ==========================================================
# 9. PART
# ==========================================================

class Part(Base):
    __tablename__ = "parts"

    part_id = Column(String(100), primary_key=True)

    name = Column(String(150), nullable=False)

    part_type = Column(String(100), nullable=False)

    unit_cost = Column(Float, nullable=False)

    stock_quantity = Column(Integer, nullable=False, default=0)

    status = Column(String(30), nullable=False, default="AVAILABLE")

    __table_args__ = (
        CheckConstraint(
            "unit_cost >= 0",
            name="ck_part_cost"
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_part_stock"
        ),
        CheckConstraint(
            "status IN "
            "('AVAILABLE', 'LOW_STOCK', 'OUT_OF_STOCK', 'DISCONTINUED')",
            name="ck_part_status"
        ),
    )

    work_order_usages = relationship(
        "WorkOrderPart",
        back_populates="part"
    )


# ==========================================================
# 10. TECHNICIAN
# ==========================================================

class Technician(Base):
    __tablename__ = "technicians"

    technician_id = Column(String(100), primary_key=True)

    name = Column(String(150), nullable=False)

    skill_specialty = Column(String(100), nullable=False)

    employment_status = Column(
        String(20),
        nullable=False,
        default="ACTIVE"
    )

    __table_args__ = (
        CheckConstraint(
            "employment_status IN ('ACTIVE', 'INACTIVE')",
            name="ck_technician_status"
        ),
    )

    work_order_assignments = relationship(
        "WorkOrderTechnician",
        back_populates="technician"
    )


# ==========================================================
# BRIDGE TABLE 1: WORK ORDER <-> PART
# ==========================================================

class WorkOrderPart(Base):
    __tablename__ = "work_order_parts"

    work_order_id = Column(
        String(100),
        ForeignKey("maintenance_work_orders.work_order_id"),
        primary_key=True
    )

    part_id = Column(
        String(100),
        ForeignKey("parts.part_id"),
        primary_key=True
    )

    quantity = Column(Integer, nullable=False)

    unit_cost_at_use = Column(Float, nullable=False)

    used_at = Column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_work_order_part_quantity"
        ),
        CheckConstraint(
            "unit_cost_at_use >= 0",
            name="ck_work_order_part_cost"
        ),
    )

    work_order = relationship(
        "MaintenanceWorkOrder",
        back_populates="parts_used"
    )

    part = relationship(
        "Part",
        back_populates="work_order_usages"
    )


# ==========================================================
# BRIDGE TABLE 2: WORK ORDER <-> TECHNICIAN
# ==========================================================

class WorkOrderTechnician(Base):
    __tablename__ = "work_order_technicians"

    work_order_id = Column(
        String(100),
        ForeignKey("maintenance_work_orders.work_order_id"),
        primary_key=True
    )

    technician_id = Column(
        String(100),
        ForeignKey("technicians.technician_id"),
        primary_key=True
    )

    assigned_at = Column(DateTime, nullable=False)

    released_at = Column(DateTime, nullable=True)

    role = Column(String(100), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "released_at IS NULL OR released_at >= assigned_at",
            name="ck_technician_assignment_dates"
        ),
    )

    work_order = relationship(
        "MaintenanceWorkOrder",
        back_populates="technician_assignments"
    )

    technician = relationship(
        "Technician",
        back_populates="work_order_assignments"
    )


# ==========================================================
# HISTORY TABLE 1: MACHINE STATE CHANGES
# ==========================================================

class MachineStateHistory(Base):
    __tablename__ = "machine_state_history"

    state_event_id = Column(String(150), primary_key=True)

    machine_id = Column(
        String(150),
        ForeignKey("machines.machine_id"),
        nullable=False
    )

    previous_state = Column(String(30), nullable=True)

    new_state = Column(String(30), nullable=False)

    changed_at = Column(DateTime, nullable=False)

    reason = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "new_state IN "
            "('RUNNING', 'IDLE', 'SHUTDOWN', 'MAINTENANCE')",
            name="ck_machine_history_state"
        ),
    )

    machine = relationship(
        "Machine",
        back_populates="state_history"
    )


# ==========================================================
# HISTORY TABLE 2: WORK ORDER STATUS CHANGES
# ==========================================================

class WorkOrderStatusHistory(Base):
    __tablename__ = "work_order_status_history"

    status_event_id = Column(String(150), primary_key=True)

    work_order_id = Column(
        String(100),
        ForeignKey("maintenance_work_orders.work_order_id"),
        nullable=False
    )

    previous_status = Column(String(30), nullable=True)

    new_status = Column(String(30), nullable=False)

    changed_at = Column(DateTime, nullable=False)

    changed_by = Column(
        String(100),
        ForeignKey("technicians.technician_id"),
        nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "new_status IN "
            "('OPEN', 'PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_work_order_history_status"
        ),
    )

    work_order = relationship(
        "MaintenanceWorkOrder",
        back_populates="status_history"
    )

    technician = relationship("Technician")
