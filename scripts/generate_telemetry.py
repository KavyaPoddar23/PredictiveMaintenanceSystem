
import argparse
import csv
import gzip
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from backend.app.database import SessionLocal
from backend.app.models import (
    Machine,
    Sensor,
    TelemetryEvent,
    MachineStateHistory,
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SEED = 20261022

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "telemetry"

START_DATE = datetime(2026, 1, 1, 0, 0, 0)
DURATION_DAYS = 90
INTERVAL_SECONDS = 1800

TOTAL_STEPS = (
    DURATION_DAYS * 24 * 60 * 60 // INTERVAL_SECONDS
)

BATCH_SIZE = 10000
COMMIT_INTERVAL = 50000

SENSOR_BASELINES = {
    "TEMP": {
        "RUNNING": 72.0,
        "IDLE": 45.0,
        "SHUTDOWN": 28.0,
    },
    "VIBRATION": {
        "RUNNING": 4.0,
        "IDLE": 1.0,
        "SHUTDOWN": 0.2,
    },
    "PRESSURE": {
        "RUNNING": 8.0,
        "IDLE": 4.0,
        "SHUTDOWN": 0.5,
    },
    "RPM": {
        "RUNNING": 1800.0,
        "IDLE": 250.0,
        "SHUTDOWN": 0.0,
    },
    "CURRENT": {
        "RUNNING": 45.0,
        "IDLE": 8.0,
        "SHUTDOWN": 0.0,
    },
}

SENSOR_NOISE = {
    "TEMP": 2.0,
    "VIBRATION": 0.35,
    "PRESSURE": 0.3,
    "RPM": 35.0,
    "CURRENT": 2.5,
}

TELEMETRY_FIELDS = [
    "telemetry_id",
    "sensor_id",
    "event_timestamp",
    "value",
    "unit",
    "operating_state",
    "quality_status",
    "issue_type",
]


# ---------------------------------------------------------
# OPERATING STATE GENERATION
# ---------------------------------------------------------

def get_operating_state(timestamp, machine_index):
    """
    Generate a deterministic operating schedule.

    Weekdays:
      06:00-22:00 = RUNNING
      22:00-06:00 = IDLE

    A small group of machines also runs the night shift.

    Weekends:
      SHUTDOWN
    """

    if timestamp.weekday() >= 5:
        return "SHUTDOWN"

    hour = timestamp.hour

    if 6 <= hour < 22:
        return "RUNNING"

    # Every tenth machine operates during the night shift.
    if machine_index % 10 == 0:
        return "RUNNING"

    return "IDLE"


def generate_state_history(machines):
    history = []

    for machine_index, machine in enumerate(machines, start=1):
        previous_state = None

        for step in range(TOTAL_STEPS):
            timestamp = START_DATE + timedelta(
                seconds=step * INTERVAL_SECONDS
            )

            current_state = get_operating_state(
                timestamp,
                machine_index,
            )

            if current_state != previous_state:
                timestamp_id = timestamp.strftime("%Y%m%dT%H%M%S")

                history.append({
                    "state_event_id": (
                        f"STATE-{machine.machine_id}-{timestamp_id}"
                    ),
                    "machine_id": machine.machine_id,
                    "previous_state": previous_state,
                    "new_state": current_state,
                    "changed_at": timestamp,
                    "reason": (
                        "INITIAL_STATE"
                        if previous_state is None
                        else "SCHEDULED_OPERATING_CYCLE"
                    ),
                })

                previous_state = current_state

    return history


# ---------------------------------------------------------
# SENSOR FAULT GENERATION
# ---------------------------------------------------------

def generate_sensor_faults(sensors, rng):
    """
    Create deterministic fault windows for a small percentage
    of sensors.

    Fault types:
      SPIKE       -> extreme value, INVALID
      FLATLINE    -> repeated constant value, SUSPECT
      OUT_OF_RANGE -> value beyond configured maximum, INVALID
    """

    faults = {}

    for sensor in sensors:
        if rng.random() < 0.04:
            start_step = rng.randint(100, TOTAL_STEPS - 100)
            duration = rng.randint(2, 8)

            faults[sensor.sensor_id] = {
                "start": start_step,
                "end": min(start_step + duration, TOTAL_STEPS),
                "type": rng.choice([
                    "SPIKE",
                    "FLATLINE",
                    "OUT_OF_RANGE",
                ]),
            }

    return faults


# ---------------------------------------------------------
# TELEMETRY VALUE GENERATION
# ---------------------------------------------------------

def generate_normal_value(sensor, operating_state, timestamp, rng):
    sensor_type = sensor.sensor_type

    baseline = SENSOR_BASELINES[sensor_type][operating_state]
    noise = SENSOR_NOISE[sensor_type]

    # Add a small daily cycle to temperature and current.
    daily_cycle = math.sin(
        (timestamp.hour / 24.0) * 2.0 * math.pi
    )

    if sensor_type == "TEMP":
        baseline += 3.0 * daily_cycle

    elif sensor_type == "CURRENT" and operating_state == "RUNNING":
        baseline += 2.0 * daily_cycle

    value = baseline + rng.gauss(0, noise)

    # Prevent small random negative readings for non-negative sensors.
    value = max(0.0, value)

    return round(value, 3)


def apply_sensor_fault(
    sensor,
    step,
    value,
    fault,
    flatline_values,
):
    if fault is None:
        return value, "VALID", None

    if not (fault["start"] <= step < fault["end"]):
        return value, "VALID", None

    fault_type = fault["type"]

    if fault_type == "SPIKE":
        return (
            round(sensor.max_valid * 1.25, 3),
            "INVALID",
            "SPIKE",
        )

    if fault_type == "OUT_OF_RANGE":
        return (
            round(sensor.max_valid + 10.0, 3),
            "INVALID",
            "OUT_OF_RANGE",
        )

    if fault_type == "FLATLINE":
        if sensor.sensor_id not in flatline_values:
            flatline_values[sensor.sensor_id] = value

        return (
            flatline_values[sensor.sensor_id],
            "SUSPECT",
            "FLATLINE",
        )

    return value, "VALID", None


# ---------------------------------------------------------
# EXPORT HELPERS
# ---------------------------------------------------------

def export_state_history(history):
    csv_path = OUTPUT_DIR / "machine_state_history.csv"
    jsonl_path = OUTPUT_DIR / "machine_state_history.jsonl"

    fields = [
        "state_event_id",
        "machine_id",
        "previous_state",
        "new_state",
        "changed_at",
        "reason",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file, jsonl_path.open(
        "w",
        encoding="utf-8",
    ) as json_file:

        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()

        for record in history:
            csv_record = {
                key: value.isoformat() if isinstance(value, datetime)
                else value
                for key, value in record.items()
            }

            writer.writerow(csv_record)
            json_file.write(
                json.dumps(csv_record) + "\n"
            )

    print(f"Created: {csv_path}")
    print(f"Created: {jsonl_path}")


# ---------------------------------------------------------
# MAIN TELEMETRY GENERATOR
# ---------------------------------------------------------

def generate_telemetry(mode):
    rng = random.Random(SEED)

    session = SessionLocal()

    try:
        machines = (
            session.query(Machine)
            .order_by(Machine.machine_id)
            .all()
        )

        sensors = (
            session.query(Sensor)
            .order_by(Sensor.sensor_id)
            .all()
        )

        expected_machines = 100 if mode == "full" else 10
        expected_sensors = 500 if mode == "full" else 50

        if len(machines) != expected_machines:
            raise ValueError(
                f"Expected {expected_machines} machines, "
                f"found {len(machines)}. Run the master generator first."
            )

        if len(sensors) != expected_sensors:
            raise ValueError(
                f"Expected {expected_sensors} sensors, "
                f"found {len(sensors)}. Run the master generator first."
            )

        if any(
            sensor.sampling_interval_seconds != INTERVAL_SECONDS
            for sensor in sensors
        ):
            raise ValueError(
                "Sensor sampling interval must be 1800 seconds. "
                "Update and rerun the master data generator."
            )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        print("Generating machine state history...")

        state_history = generate_state_history(machines)

        # Replace old generated telemetry and state history.
        # This makes reruns reproducible.
        session.query(TelemetryEvent).delete(
            synchronize_session=False
        )

        session.query(MachineStateHistory).delete(
            synchronize_session=False
        )

        session.commit()

        session.bulk_insert_mappings(
            MachineStateHistory,
            state_history,
        )
        session.commit()

        export_state_history(state_history)

        print(f"State history records: {len(state_history)}")

        print("\nPreparing sensor fault windows...")

        faults = generate_sensor_faults(sensors, rng)
        flatline_values = {}

        print(f"Fault-affected sensors: {len(faults)}")

        csv_path = OUTPUT_DIR / "telemetry_events.csv.gz"
        jsonl_path = OUTPUT_DIR / "telemetry_events.jsonl.gz"

        batch = []
        total_records = 0
        committed_records = 0

        # Assign each machine a stable index for its operating schedule.
        machine_index_by_id = {
            machine.machine_id: index
            for index, machine in enumerate(machines, start=1)
        }

        # Open compressed output files.
        with gzip.open(
            csv_path,
            "wt",
            newline="",
            encoding="utf-8",
        ) as csv_file, gzip.open(
            jsonl_path,
            "wt",
            encoding="utf-8",
        ) as json_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=TELEMETRY_FIELDS,
            )
            writer.writeheader()

            for step in range(TOTAL_STEPS):
                timestamp = START_DATE + timedelta(
                    seconds=step * INTERVAL_SECONDS
                )

                timestamp_id = timestamp.strftime("%Y%m%dT%H%M%S")

                for sensor in sensors:
                    machine_index = machine_index_by_id[
                        sensor.machine_id
                    ]

                    operating_state = get_operating_state(
                        timestamp,
                        machine_index,
                    )

                    value = generate_normal_value(
                        sensor,
                        operating_state,
                        timestamp,
                        rng,
                    )

                    value, quality_status, issue_type = (
                        apply_sensor_fault(
                            sensor,
                            step,
                            value,
                            faults.get(sensor.sensor_id),
                            flatline_values,
                        )
                    )

                    telemetry_id = (
                        f"TEL-{sensor.sensor_id}-{timestamp_id}"
                    )

                    record = {
                        "telemetry_id": telemetry_id,
                        "sensor_id": sensor.sensor_id,
                        "event_timestamp": timestamp,
                        "value": value,
                        "unit": sensor.unit,
                        "operating_state": operating_state,
                        "quality_status": quality_status,
                        "issue_type": issue_type,
                    }

                    csv_record = {
                        key: (
                            value.isoformat()
                            if isinstance(value, datetime)
                            else value
                        )
                        for key, value in record.items()
                    }

                    writer.writerow(csv_record)
                    json_file.write(
                        json.dumps(csv_record) + "\n"
                    )

                    batch.append(record)
                    total_records += 1

                    if len(batch) >= BATCH_SIZE:
                        session.bulk_insert_mappings(
                            TelemetryEvent,
                            batch,
                        )
                        batch.clear()

                    if total_records % COMMIT_INTERVAL == 0:
                        if batch:
                            session.bulk_insert_mappings(
                                TelemetryEvent,
                                batch,
                            )
                            batch.clear()

                        session.commit()
                        committed_records = total_records

                        print(
                            f"Generated and saved "
                            f"{total_records:,} telemetry readings..."
                        )

            # Save remaining records.
            if batch:
                session.bulk_insert_mappings(
                    TelemetryEvent,
                    batch,
                )
                batch.clear()

            session.commit()

        actual_count = (
            session.query(TelemetryEvent).count()
        )

        print("\n" + "=" * 60)
        print("TELEMETRY GENERATION SUMMARY")
        print("=" * 60)
        print(f"Mode: {mode}")
        print(f"Machines: {len(machines)}")
        print(f"Sensors: {len(sensors)}")
        print(f"Days: {DURATION_DAYS}")
        print(f"Interval: {INTERVAL_SECONDS} seconds")
        print(f"Generated readings: {total_records:,}")
        print(f"Database readings: {actual_count:,}")
        print(f"State history records: {len(state_history):,}")
        print(f"Fault-affected sensors: {len(faults)}")
        print(f"CSV: {csv_path}")
        print(f"JSONL: {jsonl_path}")

        if actual_count != total_records:
            raise RuntimeError(
                "Database count does not match generated record count."
            )

        print("\nTelemetry generation completed successfully.")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic industrial telemetry."
    )

    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("INDUSTRIAL PREDICTIVE MAINTENANCE")
    print("TELEMETRY GENERATOR")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Seed: {SEED}")
    print(f"Total time steps: {TOTAL_STEPS:,}")

    generate_telemetry(args.mode)


if __name__ == "__main__":
    main()
