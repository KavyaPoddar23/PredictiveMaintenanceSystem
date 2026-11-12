
import argparse
import csv
import json
import random
from datetime import date, datetime, time
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import (
    Plant,
    ProductionLine,
    Machine,
    Sensor,
    OperatingShift,
    Part,
    Technician,
)


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

SEED = 20261022
BASE_DIR = Path(__file__).resolve().parents[1]
MASTER_DATA_DIR = BASE_DIR / "data" / "master"

REFERENCE_DATE = date(2026, 1, 1)
REFERENCE_DATETIME = datetime(2026, 1, 1, 0, 0, 0)

SENSOR_CONFIG = {
    "TEMP": {
        "unit": "degC",
        "min_valid": -20.0,
        "max_valid": 180.0,
    },
    "VIBRATION": {
        "unit": "mm/s",
        "min_valid": 0.0,
        "max_valid": 50.0,
    },
    "PRESSURE": {
        "unit": "bar",
        "min_valid": 0.0,
        "max_valid": 25.0,
    },
    "RPM": {
        "unit": "rpm",
        "min_valid": 0.0,
        "max_valid": 6000.0,
    },
    "CURRENT": {
        "unit": "A",
        "min_valid": 0.0,
        "max_valid": 200.0,
    },
}

MACHINE_TYPES = [
    "CNC_LATHE",
    "HYDRAULIC_PRESS",
    "CONVEYOR",
    "INDUSTRIAL_PUMP",
    "AIR_COMPRESSOR",
    "INDUSTRIAL_MOTOR",
    "PACKAGING_MACHINE",
    "MILLING_MACHINE",
]

MANUFACTURERS = [
    "Siemens",
    "ABB",
    "Bosch",
    "Schneider Electric",
    "Mitsubishi",
]

PLANT_LOCATIONS = [
    ("Jaipur Plant", "Jaipur, Rajasthan"),
    ("Pune Plant", "Pune, Maharashtra"),
    ("Bengaluru Plant", "Bengaluru, Karnataka"),
]

LINE_NAMES = [
    "Assembly Line",
    "Processing Line",
    "Packaging Line",
    "Quality Control Line",
]

PART_NAMES = [
    ("Bearing", "MECHANICAL"),
    ("Motor Belt", "MECHANICAL"),
    ("Hydraulic Seal", "HYDRAULIC"),
    ("Temperature Probe", "SENSOR"),
    ("Vibration Sensor", "SENSOR"),
    ("Pressure Valve", "HYDRAULIC"),
    ("Cooling Fan", "ELECTRICAL"),
    ("Drive Motor", "ELECTRICAL"),
    ("Oil Filter", "CONSUMABLE"),
    ("Gear Assembly", "MECHANICAL"),
    ("Power Relay", "ELECTRICAL"),
    ("Pump Impeller", "MECHANICAL"),
    ("Circuit Breaker", "ELECTRICAL"),
    ("Lubrication Unit", "CONSUMABLE"),
    ("Pressure Gauge", "SENSOR"),
    ("Control Module", "ELECTRONIC"),
    ("Conveyor Roller", "MECHANICAL"),
    ("Air Filter", "CONSUMABLE"),
    ("Cooling Pump", "MECHANICAL"),
    ("Encoder", "SENSOR"),
    ("Hydraulic Hose", "HYDRAULIC"),
    ("Motor Coupling", "MECHANICAL"),
    ("Power Supply", "ELECTRICAL"),
    ("Flow Meter", "SENSOR"),
    ("Safety Switch", "ELECTRICAL"),
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Ishaan",
    "Riya", "Ananya", "Diya", "Meera", "Kavya",
    "Rahul", "Neha", "Amit", "Priya", "Karan",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Mehta", "Patel",
    "Singh", "Rao", "Kumar", "Joshi", "Das",
]


# ---------------------------------------------------------
# DATA GENERATION
# ---------------------------------------------------------

def generate_plants():
    plants = []

    for index, (plant_name, location) in enumerate(PLANT_LOCATIONS, start=1):
        plants.append({
            "plant_id": f"PLT-{index:03d}",
            "name": plant_name,
            "location": location,
            "timezone": "Asia/Kolkata",
            "status": "ACTIVE",
            "created_at": REFERENCE_DATETIME,
        })

    return plants


def generate_production_lines(plants, line_limit):
    lines = []

    for plant in plants:
        for line_number in range(1, line_limit + 1):
            line_name = LINE_NAMES[line_number - 1]

            lines.append({
                "line_id": (
                    f"LINE-{plant['plant_id']}-{line_number:03d}"
                ),
                "plant_id": plant["plant_id"],
                "name": line_name,
                "status": "ACTIVE",
                "effective_from": REFERENCE_DATE,
                "effective_to": None,
            })

    return lines


def generate_machines(lines, machines_per_line, rng):
    machines = []

    for line_index, line in enumerate(lines):
        for machine_number in range(1, machines_per_line[line_index] + 1):
            machine_id = (
                f"MCH-{line['line_id']}-{machine_number:03d}"
            )

            machines.append({
                "machine_id": machine_id,
                "line_id": line["line_id"],
                "name": f"Machine {machine_number:03d}",
                "machine_type": rng.choice(MACHINE_TYPES),
                "manufacturer": rng.choice(MANUFACTURERS),
                "model": f"MODEL-{rng.randint(100, 999)}",
                "install_date": date(
                    2024,
                    rng.randint(1, 12),
                    rng.randint(1, 28),
                ),
                "criticality": rng.choice(
                    ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                ),
                "lifecycle_state": "ACTIVE",
                "operating_state": "RUNNING",
                "created_at": REFERENCE_DATETIME,
            })

    return machines


def generate_sensors(machines):
    sensors = []

    for machine in machines:
        for sensor_type, config in SENSOR_CONFIG.items():
            sensor_id = (
                f"SNS-{machine['machine_id']}-{sensor_type}-01"
            )

            sensors.append({
                "sensor_id": sensor_id,
                "machine_id": machine["machine_id"],
                "sensor_type": sensor_type,
                "unit": config["unit"],
                "min_valid": config["min_valid"],
                "max_valid": config["max_valid"],
                "sampling_interval_seconds": 1800,
                "status": "ACTIVE",
                "installed_at": REFERENCE_DATETIME,
                "removed_at": None,
            })

    return sensors


def generate_operating_shifts(plants):
    shift_definitions = [
        ("DAY", time(6, 0), time(14, 0)),
        ("EVENING", time(14, 0), time(22, 0)),
        ("NIGHT", time(22, 0), time(6, 0)),
    ]

    shifts = []

    for plant in plants:
        for shift_name, starts_at, ends_at in shift_definitions:
            shifts.append({
                "shift_id": (
                    f"SHIFT-{plant['plant_id']}-{shift_name}"
                ),
                "plant_id": plant["plant_id"],
                "shift_name": shift_name,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "effective_from": REFERENCE_DATE,
                "effective_to": None,
                "status": "ACTIVE",
            })

    return shifts


def generate_parts(part_limit):
    parts = []

    for index, (part_name, part_type) in enumerate(
        PART_NAMES[:part_limit], start=1
    ):
        parts.append({
            "part_id": f"PART-{index:03d}",
            "name": part_name,
            "part_type": part_type,
            "unit_cost": round(250 + index * 175.50, 2),
            "stock_quantity": 20 + index * 3,
            "status": "AVAILABLE",
        })

    return parts


def generate_technicians(technician_limit, rng):
    specialties = [
        "MECHANICAL",
        "ELECTRICAL",
        "HYDRAULIC",
        "INSTRUMENTATION",
        "GENERAL_MAINTENANCE",
    ]

    technicians = []

    for index in range(1, technician_limit + 1):
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)

        technicians.append({
            "technician_id": f"TECH-{index:03d}",
            "name": f"{first_name} {last_name}",
            "skill_specialty": specialties[(index - 1) % len(specialties)],
            "employment_status": "ACTIVE",
        })

    return technicians


# ---------------------------------------------------------
# CSV AND JSON EXPORT
# ---------------------------------------------------------

def serialize_value(value):
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()

    return value


def export_csv(filename, records):
    if not records:
        return

    output_path = MASTER_DATA_DIR / f"{filename}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys()),
        )
        writer.writeheader()

        for record in records:
            writer.writerow({
                key: serialize_value(value)
                for key, value in record.items()
            })

    print(f"Created: {output_path}")


def export_json(filename, records):
    output_path = MASTER_DATA_DIR / f"{filename}.json"

    serializable_records = [
        {
            key: serialize_value(value)
            for key, value in record.items()
        }
        for record in records
    ]

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            serializable_records,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"Created: {output_path}")


# ---------------------------------------------------------
# DATABASE INSERTION
# ---------------------------------------------------------

def insert_into_database(dataset):
    model_mapping = [
        ("plants", Plant),
        ("production_lines", ProductionLine),
        ("machines", Machine),
        ("sensors", Sensor),
        ("operating_shifts", OperatingShift),
        ("parts", Part),
        ("technicians", Technician),
    ]

    session: Session = SessionLocal()

    try:
        for dataset_name, model_class in model_mapping:
            records = dataset[dataset_name]

            for record in records:
                # merge() makes rerunning the same generator
                # safe for records with the same primary key.
                session.merge(model_class(**record))

        session.commit()
        print("\nMaster data successfully inserted into SQLite.")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def validate_dataset(dataset, mode):
    plants = dataset["plants"]
    lines = dataset["production_lines"]
    machines = dataset["machines"]
    sensors = dataset["sensors"]
    shifts = dataset["operating_shifts"]
    parts = dataset["parts"]
    technicians = dataset["technicians"]

    assert len(plants) == (3 if mode == "full" else 1)
    assert len(lines) == (12 if mode == "full" else 2)
    assert len(machines) == (100 if mode == "full" else 10)
    assert len(sensors) == (500 if mode == "full" else 50)

    # Primary key uniqueness
    for collection, primary_key in [
        (plants, "plant_id"),
        (lines, "line_id"),
        (machines, "machine_id"),
        (sensors, "sensor_id"),
        (shifts, "shift_id"),
        (parts, "part_id"),
        (technicians, "technician_id"),
    ]:
        values = [record[primary_key] for record in collection]
        assert len(values) == len(set(values)), (
            f"Duplicate primary key found in {primary_key}"
        )

    # Foreign key integrity
    plant_ids = {p["plant_id"] for p in plants}
    line_ids = {line["line_id"] for line in lines}
    machine_ids = {machine["machine_id"] for machine in machines}

    assert all(line["plant_id"] in plant_ids for line in lines)
    assert all(machine["line_id"] in line_ids for machine in machines)
    assert all(sensor["machine_id"] in machine_ids for sensor in sensors)
    assert all(shift["plant_id"] in plant_ids for shift in shifts)

    # Sensor unit and range checks
    for sensor in sensors:
        config = SENSOR_CONFIG[sensor["sensor_type"]]
        assert sensor["unit"] == config["unit"]
        assert sensor["min_valid"] < sensor["max_valid"]
        assert sensor["sampling_interval_seconds"] > 0

    # Exactly five sensor types per machine
    for machine in machines:
        machine_sensors = [
            sensor for sensor in sensors
            if sensor["machine_id"] == machine["machine_id"]
        ]
        assert len(machine_sensors) == 5

    print("\nAll master-data validation checks passed.")


# ---------------------------------------------------------
# MAIN GENERATOR
# ---------------------------------------------------------

def generate_dataset(mode):
    rng = random.Random(SEED)

    if mode == "full":
        plant_limit = 3
        line_limit = 4
        machines_per_line = [9, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8]
        part_limit = 25
        technician_limit = 30
    else:
        plant_limit = 1
        line_limit = 2
        machines_per_line = [5, 5]
        part_limit = 8
        technician_limit = 10

    plants = generate_plants()[:plant_limit]
    lines = generate_production_lines(plants, line_limit)
    machines = generate_machines(lines, machines_per_line, rng)
    sensors = generate_sensors(machines)
    shifts = generate_operating_shifts(plants)
    parts = generate_parts(part_limit)
    technicians = generate_technicians(technician_limit, rng)

    dataset = {
        "plants": plants,
        "production_lines": lines,
        "machines": machines,
        "sensors": sensors,
        "operating_shifts": shifts,
        "parts": parts,
        "technicians": technicians,
    }

    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Generate deterministic industrial master data."
    )

    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter",
        help="Choose starter or full synthetic dataset.",
    )

    args = parser.parse_args()

    MASTER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("INDUSTRIAL PREDICTIVE MAINTENANCE")
    print("SYNTHETIC MASTER DATA GENERATOR")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Random seed: {SEED}")

    dataset = generate_dataset(args.mode)

    validate_dataset(dataset, args.mode)

    for name, records in dataset.items():
        export_csv(name, records)
        export_json(name, records)

    insert_into_database(dataset)

    print("\nGENERATED RECORD COUNTS")
    print("-" * 35)

    for name, records in dataset.items():
        print(f"{name:25s}: {len(records):>5}")

    print("\nPhase 3 master data generation completed.")


if __name__ == "__main__":
    main()
