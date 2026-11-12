
from sqlalchemy import func

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

EXPECTED_COUNTS = {
    "plants": (Plant, 3),
    "production_lines": (ProductionLine, 12),
    "machines": (Machine, 100),
    "sensors": (Sensor, 500),
    "operating_shifts": (OperatingShift, 9),
    "parts": (Part, 25),
    "technicians": (Technician, 30),
}


def main():
    session = SessionLocal()
    all_passed = True

    try:
        print("=" * 55)
        print("MASTER DATA DATABASE VERIFICATION")
        print("=" * 55)

        for name, (model, expected) in EXPECTED_COUNTS.items():
            actual = session.query(model).count()
            passed = actual == expected

            print(
                f"{name:25s} Expected: {expected:4d} "
                f"Actual: {actual:4d} "
                f"{'PASSED' if passed else 'FAILED'}"
            )

            if not passed:
                all_passed = False

        print("\nSENSOR DISTRIBUTION CHECK")

        sensor_counts = (
            session.query(
                Sensor.machine_id,
                func.count(Sensor.sensor_id),
            )
            .group_by(Sensor.machine_id)
            .all()
        )

        correct_distribution = (
            len(sensor_counts) == 100
            and all(count == 5 for _, count in sensor_counts)
        )

        print(
            "Every machine has exactly five sensors:",
            "PASSED" if correct_distribution else "FAILED",
        )

        if not correct_distribution:
            all_passed = False

        print("\nFOREIGN KEY CHECK")

        invalid_lines = (
            session.query(ProductionLine)
            .filter(~ProductionLine.plant_id.in_(
                session.query(Plant.plant_id)
            ))
            .count()
        )

        invalid_machines = (
            session.query(Machine)
            .filter(~Machine.line_id.in_(
                session.query(ProductionLine.line_id)
            ))
            .count()
        )

        invalid_sensors = (
            session.query(Sensor)
            .filter(~Sensor.machine_id.in_(
                session.query(Machine.machine_id)
            ))
            .count()
        )

        fk_passed = (
            invalid_lines == 0
            and invalid_machines == 0
            and invalid_sensors == 0
        )

        print(
            "Plant, line, machine and sensor references:",
            "PASSED" if fk_passed else "FAILED",
        )

        if not fk_passed:
            all_passed = False

        print("\n" + "=" * 55)

        if all_passed:
            print("ALL MASTER DATA CHECKS PASSED!")
        else:
            print("SOME MASTER DATA CHECKS FAILED.")
            raise SystemExit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
