
import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import (
    Machine,
    Sensor,
    TelemetryEvent,
    MaintenanceWorkOrder,
    FailureEvent,
    Part,
    Technician,
    WorkOrderPart,
    WorkOrderTechnician,
    WorkOrderStatusHistory,
    MachineStateHistory,
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SEED = 20261022

BASE_DIR = Path(__file__).resolve().parents[1]

MASTER_DIR = BASE_DIR / "data" / "master"
TRANSACTION_DIR = BASE_DIR / "data" / "transactions"
GROUND_TRUTH_DIR = BASE_DIR / "data" / "ground_truth"

START_DATE = datetime(2026, 1, 1)
DURATION_DAYS = 90

FAILURE_COUNT_FULL = 120
FAILURE_COUNT_STARTER = 12

DEGRADATION_HOURS = 48

FAILURE_TYPES = [
    "OVERHEATING",
    "EXCESSIVE_VIBRATION",
    "PRESSURE_DROP",
    "MOTOR_OVERLOAD",
    "BEARING_FAILURE",
]

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

FAILURE_SENSOR_MAPPING = {
    "OVERHEATING": "TEMP",
    "EXCESSIVE_VIBRATION": "VIBRATION",
    "PRESSURE_DROP": "PRESSURE",
    "MOTOR_OVERLOAD": "CURRENT",
    "BEARING_FAILURE": "VIBRATION",
}

# Degradation amounts applied progressively over the
# 48 hours before a failure.
DEGRADATION_AMOUNTS = {
    "TEMP": 12.0,
    "VIBRATION": 4.0,
    "PRESSURE": -2.0,
    "CURRENT": 10.0,
    "RPM": -100.0,
}


# ---------------------------------------------------------
# FILE HELPERS
# ---------------------------------------------------------

def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys()),
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Created: {path}")


def load_master_parts():
    path = MASTER_DIR / "parts.csv"

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def iso(value):
    return value.isoformat() if value is not None else None


# ---------------------------------------------------------
# FAILURE SCHEDULE
# ---------------------------------------------------------

def generate_failure_schedule(machines, failure_count, rng):
    """
    Generate 120 failure events.

    The first 100 events cover all 100 machines.
    The remaining 20 events are assigned to 20 machines
    that experience a second failure.

    Failure dates are distributed throughout the 90-day
    observation window.
    """

    if failure_count > len(machines) * 2:
        raise ValueError("Too many failures for this generator.")

    schedule = []

    for index in range(failure_count):
        machine_index = index % len(machines)
        occurrence_number = index // len(machines)

        machine = machines[machine_index]

        day_offset = 15 + (
            (machine_index * 7 + occurrence_number * 23) % 70
        )

        hour = rng.randint(0, 23)
        minute = rng.choice([0, 30])

        occurred_at = (
            START_DATE
            + timedelta(
                days=day_offset,
                hours=hour,
                minutes=minute,
            )
        )

        failure_type = rng.choice(FAILURE_TYPES)
        severity = rng.choices(
            SEVERITIES,
            weights=[10, 30, 40, 20],
            k=1,
        )[0]

        downtime_hours = rng.randint(2, 18)

        schedule.append({
            "machine": machine,
            "occurred_at": occurred_at,
            "failure_type": failure_type,
            "severity": severity,
            "downtime_hours": downtime_hours,
        })

    schedule.sort(key=lambda item: item["occurred_at"])

    return schedule


# ---------------------------------------------------------
# PRE-FAILURE DEGRADATION
# ---------------------------------------------------------

def apply_pre_failure_degradation(
    session,
    machine,
    occurred_at,
    failure_type,
):
    """
    Modify existing telemetry in the 48-hour window before
    failure so the sensor pattern reflects degradation.

    Only VALID readings are modified.

    The failure label itself is never written to telemetry.
    """

    symptom_start = (
        occurred_at - timedelta(hours=DEGRADATION_HOURS)
    )

    sensors = (
        session.query(Sensor)
        .filter(Sensor.machine_id == machine.machine_id)
        .all()
    )

    primary_sensor_type = FAILURE_SENSOR_MAPPING[failure_type]

    updated_count = 0

    for sensor in sensors:
        amount = DEGRADATION_AMOUNTS.get(sensor.sensor_type, 0.0)

        # Apply stronger degradation to the sensor most
        # relevant to the failure type.
        if sensor.sensor_type == primary_sensor_type:
            amount *= 1.5

        if amount == 0:
            continue

        readings = (
            session.query(TelemetryEvent)
            .filter(
                TelemetryEvent.sensor_id == sensor.sensor_id,
                TelemetryEvent.event_timestamp >= symptom_start,
                TelemetryEvent.event_timestamp < occurred_at,
                TelemetryEvent.quality_status == "VALID",
            )
            .all()
        )

        for reading in readings:
            elapsed = (
                reading.event_timestamp - symptom_start
            ).total_seconds()

            total_seconds = DEGRADATION_HOURS * 3600

            progress = elapsed / total_seconds

            new_value = reading.value + amount * progress

            # Keep readings inside their configured sensor range.
            new_value = max(sensor.min_valid, new_value)
            new_value = min(sensor.max_valid, new_value)

            reading.value = round(new_value, 3)
            updated_count += 1

    return updated_count


# ---------------------------------------------------------
# WORK ORDER AND FAILURE RECORDS
# ---------------------------------------------------------

def build_transaction_records(schedule, parts, technicians, rng):
    work_orders = []
    failures = []
    parts_used = []
    assignments = []
    status_history = []
    machine_state_history = []
    ground_truth = []

    part_usage_totals = {
        part["part_id"]: 0
        for part in parts
    }

    technician_ids = [
        technician.technician_id
        for technician in technicians
    ]

    part_ids = [
        part["part_id"]
        for part in parts
    ]

    for index, item in enumerate(schedule, start=1):
        machine = item["machine"]
        occurred_at = item["occurred_at"]
        failure_type = item["failure_type"]
        severity = item["severity"]
        downtime_hours = item["downtime_hours"]

        work_order_id = f"WO-2026-{index:06d}"
        failure_event_id = f"FAIL-2026-{index:06d}"

        symptom_at = occurred_at - timedelta(hours=24)
        opened_at = occurred_at - timedelta(hours=2)
        actual_start = occurred_at
        actual_end = occurred_at + timedelta(hours=downtime_hours)

        maintenance_type = "CORRECTIVE"
        priority = severity

        work_orders.append({
            "work_order_id": work_order_id,
            "machine_id": machine.machine_id,
            "maintenance_type": maintenance_type,
            "priority": priority,
            "status": "COMPLETED",
            "reason": f"Repair after {failure_type}",
            "opened_at": opened_at,
            "planned_start": actual_start,
            "actual_start": actual_start,
            "actual_end": actual_end,
            "notes": (
                f"Synthetic corrective maintenance for "
                f"{failure_type}. Downtime: {downtime_hours} hours."
            ),
        })

        failures.append({
            "failure_event_id": failure_event_id,
            "machine_id": machine.machine_id,
            "work_order_id": work_order_id,
            "failure_type": failure_type,
            "severity": severity,
            "symptom_first_observed_at": symptom_at,
            "occurred_at": occurred_at,
            "downtime_start": occurred_at,
            "downtime_end": actual_end,
            "root_cause": (
                f"Synthetic {failure_type.lower()} degradation pattern"
            ),
        })

        # Use one or two parts for each repair.
        selected_parts = rng.sample(
            part_ids,
            k=rng.choice([1, 2]),
        )

        for part_id in selected_parts:
            quantity = rng.randint(1, 2)

            part_usage_totals[part_id] += quantity

            part = next(
                item for item in parts
                if item["part_id"] == part_id
            )

            parts_used.append({
                "work_order_id": work_order_id,
                "part_id": part_id,
                "quantity": quantity,
                "unit_cost_at_use": float(part["unit_cost"]),
                "used_at": actual_start + timedelta(minutes=30),
            })

        # Assign one or two technicians to each work order.
        selected_technicians = rng.sample(
            technician_ids,
            k=rng.choice([1, 2]),
        )

        for technician_id in selected_technicians:
            assignments.append({
                "work_order_id": work_order_id,
                "technician_id": technician_id,
                "assigned_at": opened_at,
                "released_at": actual_end,
                "role": "LEAD" if technician_id == selected_technicians[0]
                else "SUPPORT",
            })

        lead_technician = selected_technicians[0]

        # Preserve every status transition.
        status_history.extend([
            {
                "status_event_id": f"WOST-{index:06d}-001",
                "work_order_id": work_order_id,
                "previous_status": None,
                "new_status": "OPEN",
                "changed_at": opened_at,
                "changed_by": None,
            },
            {
                "status_event_id": f"WOST-{index:06d}-002",
                "work_order_id": work_order_id,
                "previous_status": "OPEN",
                "new_status": "IN_PROGRESS",
                "changed_at": actual_start,
                "changed_by": lead_technician,
            },
            {
                "status_event_id": f"WOST-{index:06d}-003",
                "work_order_id": work_order_id,
                "previous_status": "IN_PROGRESS",
                "new_status": "COMPLETED",
                "changed_at": actual_end,
                "changed_by": lead_technician,
            },
        ])

        # Record machine state changes explicitly.
        machine_state_history.extend([
            {
                "state_event_id": (
                    f"MAINT-STATE-{index:06d}-001"
                ),
                "machine_id": machine.machine_id,
                "previous_state": "RUNNING",
                "new_state": "MAINTENANCE",
                "changed_at": actual_start,
                "reason": f"FAILURE-{failure_type}",
            },
            {
                "state_event_id": (
                    f"MAINT-STATE-{index:06d}-002"
                ),
                "machine_id": machine.machine_id,
                "previous_state": "MAINTENANCE",
                "new_state": "RUNNING",
                "changed_at": actual_end,
                "reason": "REPAIR_COMPLETED",
            },
        ])

        # Ground truth is deliberately separate from telemetry.
        ground_truth.append({
            "failure_event_id": failure_event_id,
            "machine_id": machine.machine_id,
            "failure_occurred": 1,
            "failure_timestamp": iso(occurred_at),
            "symptom_first_observed_at": iso(symptom_at),
            "label_window_start": iso(
                occurred_at - timedelta(hours=24)
            ),
            "label_window_end": iso(occurred_at),
            "failure_type": failure_type,
            "severity": severity,
        })

    return {
        "work_orders": work_orders,
        "failures": failures,
        "parts_used": parts_used,
        "assignments": assignments,
        "status_history": status_history,
        "machine_state_history": machine_state_history,
        "ground_truth": ground_truth,
        "part_usage_totals": part_usage_totals,
    }


# ---------------------------------------------------------
# DATABASE INSERTION
# ---------------------------------------------------------

def clear_previous_generated_records(session):
    """
    Delete prior generated maintenance records in child-first order.
    Keep telemetry and the original telemetry state history.
    """

    session.query(WorkOrderPart).delete(
        synchronize_session=False
    )

    session.query(WorkOrderTechnician).delete(
        synchronize_session=False
    )

    session.query(WorkOrderStatusHistory).delete(
        synchronize_session=False
    )

    session.query(FailureEvent).delete(
        synchronize_session=False
    )

    session.query(MaintenanceWorkOrder).delete(
        synchronize_session=False
    )

    session.query(MachineStateHistory).filter(
        MachineStateHistory.state_event_id.like("MAINT-STATE-%")
    ).delete(synchronize_session=False)

    session.flush()


def insert_records(session, records):
    session.bulk_insert_mappings(
        MaintenanceWorkOrder,
        records["work_orders"],
    )

    session.bulk_insert_mappings(
        FailureEvent,
        records["failures"],
    )

    session.bulk_insert_mappings(
        WorkOrderPart,
        records["parts_used"],
    )

    session.bulk_insert_mappings(
        WorkOrderTechnician,
        records["assignments"],
    )

    session.bulk_insert_mappings(
        WorkOrderStatusHistory,
        records["status_history"],
    )

    session.bulk_insert_mappings(
        MachineStateHistory,
        records["machine_state_history"],
    )


def update_part_inventory(session, records, parts):
    """
    Restore baseline inventory from parts.csv, then deduct
    the quantities used by generated work orders.
    """

    for part in parts:
        part_record = session.get(Part, part["part_id"])

        baseline_quantity = int(part["stock_quantity"])

        used_quantity = records["part_usage_totals"][
            part["part_id"]
        ]

        remaining = baseline_quantity - used_quantity

        if remaining < 0:
            raise ValueError(
                f"Part inventory became negative: {part['part_id']}"
            )

        part_record.stock_quantity = remaining

        if remaining == 0:
            part_record.status = "OUT_OF_STOCK"
        elif remaining <= 10:
            part_record.status = "LOW_STOCK"
        else:
            part_record.status = "AVAILABLE"


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def validate_records(records, failure_count):
    work_orders = records["work_orders"]
    failures = records["failures"]
    parts_used = records["parts_used"]
    assignments = records["assignments"]
    status_history = records["status_history"]

    assert len(work_orders) == failure_count
    assert len(failures) == failure_count
    assert len({x["work_order_id"] for x in work_orders}) == failure_count
    assert len({x["failure_event_id"] for x in failures}) == failure_count

    assert all(
        item["symptom_first_observed_at"] < item["occurred_at"]
        for item in failures
    )

    assert all(
        item["downtime_end"] >= item["downtime_start"]
        for item in failures
    )

    assert all(
        item["actual_end"] >= item["actual_start"]
        for item in work_orders
    )

    assert all(
        item["quantity"] > 0
        and item["unit_cost_at_use"] >= 0
        for item in parts_used
    )

    assert len(status_history) == failure_count * 3

    assert all(
        item["released_at"] >= item["assigned_at"]
        for item in assignments
    )

    print("All maintenance record validation checks passed.")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic maintenance history and failures."
    )

    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter",
    )

    args = parser.parse_args()

    rng = random.Random(SEED)

    failure_count = (
        FAILURE_COUNT_FULL
        if args.mode == "full"
        else FAILURE_COUNT_STARTER
    )

    TRANSACTION_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    session: Session = SessionLocal()

    try:
        machines = (
            session.query(Machine)
            .order_by(Machine.machine_id)
            .all()
        )

        technicians = (
            session.query(Technician)
            .order_by(Technician.technician_id)
            .all()
        )

        parts = load_master_parts()

        if not machines or not technicians or not parts:
            raise ValueError(
                "Master data is missing. Generate full master data first."
            )

        if args.mode == "full" and len(machines) != 100:
            raise ValueError(
                "Full mode requires 100 machines."
            )

        if len(technicians) < 2 or len(parts) < 2:
            raise ValueError(
                "At least two technicians and two parts are required."
            )

        if failure_count > len(machines) * 2:
            raise ValueError(
                "Failure count exceeds the supported machine allocation."
            )

        print("=" * 60)
        print("MAINTENANCE AND FAILURE DATA GENERATOR")
        print("=" * 60)
        print(f"Mode: {args.mode}")
        print(f"Seed: {SEED}")
        print(f"Machines: {len(machines)}")
        print(f"Failures to generate: {failure_count}")

        schedule = generate_failure_schedule(
            machines,
            failure_count,
            rng,
        )

        print("\nApplying pre-failure telemetry degradation...")

        degradation_count = 0

        for item in schedule:
            degradation_count += apply_pre_failure_degradation(
                session,
                item["machine"],
                item["occurred_at"],
                item["failure_type"],
            )

        session.commit()

        print(
            f"Telemetry readings updated: {degradation_count:,}"
        )

        records = build_transaction_records(
            schedule,
            parts,
            technicians,
            rng,
        )

        validate_records(records, failure_count)

        print("\nReplacing previous generated maintenance records...")

        clear_previous_generated_records(session)

        insert_records(session, records)

        update_part_inventory(session, records, parts)

        session.commit()

        # Export transaction records.
        export_groups = [
            ("maintenance_work_orders", records["work_orders"]),
            ("failure_events", records["failures"]),
            ("work_order_parts", records["parts_used"]),
            ("work_order_technicians", records["assignments"]),
            ("work_order_status_history", records["status_history"]),
            (
                "maintenance_machine_state_history",
                records["machine_state_history"],
            ),
        ]

        for filename, rows in export_groups:
            export_rows = [
                {
                    key: iso(value) if isinstance(value, datetime)
                    else value
                    for key, value in row.items()
                }
                for row in rows
            ]

            write_csv(
                TRANSACTION_DIR / f"{filename}.csv",
                export_rows,
            )

        # Export labels separately.
        write_csv(
            GROUND_TRUTH_DIR / "failure_labels.csv",
            records["ground_truth"],
        )

        print("\nDATABASE RECORD COUNTS")
        print("-" * 40)

        print(
            "Maintenance work orders:",
            session.query(MaintenanceWorkOrder).count(),
        )
        print(
            "Failure events:",
            session.query(FailureEvent).count(),
        )
        print(
            "Part usage records:",
            session.query(WorkOrderPart).count(),
        )
        print(
            "Technician assignments:",
            session.query(WorkOrderTechnician).count(),
        )
        print(
            "Work-order status events:",
            session.query(WorkOrderStatusHistory).count(),
        )

        print("\nGround-truth labels are stored separately.")
        print("Maintenance generation completed successfully.")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()
