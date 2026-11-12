
from pathlib import Path

from sqlalchemy import func

from backend.app.database import engine, SessionLocal
from backend.app.models import (
    Sensor,
    TelemetryEvent,
    MachineStateHistory,
)

EXPECTED_SENSORS = 500
EXPECTED_DAYS = 90
READINGS_PER_DAY = 48

EXPECTED_READINGS = (
    EXPECTED_SENSORS
    * EXPECTED_DAYS
    * READINGS_PER_DAY
)

OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "telemetry"
)


def main():
    session = SessionLocal()
    all_passed = True

    try:
        print("=" * 60)
        print("TELEMETRY DATA VALIDATION")
        print("=" * 60)

        sensor_count = session.query(Sensor).count()
        telemetry_count = session.query(TelemetryEvent).count()
        state_count = session.query(MachineStateHistory).count()

        print("\n1. RECORD COUNTS")

        checks = [
            ("Sensors", sensor_count, EXPECTED_SENSORS),
            ("Telemetry readings", telemetry_count, EXPECTED_READINGS),
        ]

        for label, actual, expected in checks:
            passed = actual == expected

            print(
                f"{label:25s} Expected: {expected:>10,} "
                f"Actual: {actual:>10,} "
                f"{'PASSED' if passed else 'FAILED'}"
            )

            if not passed:
                all_passed = False

        print(
            f"{'Machine state events':25s}: {state_count:>10,}"
        )

        print("\n2. SENSOR COVERAGE")

        sensor_distribution = (
            session.query(
                TelemetryEvent.sensor_id,
                func.count(TelemetryEvent.telemetry_id),
            )
            .group_by(TelemetryEvent.sensor_id)
            .all()
        )

        coverage_passed = (
            len(sensor_distribution) == EXPECTED_SENSORS
            and all(
                count == EXPECTED_DAYS * READINGS_PER_DAY
                for _, count in sensor_distribution
            )
        )

        print(
            "Every sensor has 4,320 readings:",
            "PASSED" if coverage_passed else "FAILED",
        )

        if not coverage_passed:
            all_passed = False

        print("\n3. DATA QUALITY")

        quality_counts = (
            session.query(
                TelemetryEvent.quality_status,
                func.count(TelemetryEvent.telemetry_id),
            )
            .group_by(TelemetryEvent.quality_status)
            .all()
        )

        quality_total = sum(count for _, count in quality_counts)
        quality_map = dict(quality_counts)

        for quality, count in sorted(quality_counts):
            print(f"{quality:15s}: {count:>12,}")

        quality_passed = (
            quality_total == telemetry_count
            and quality_map.get("VALID", 0) > 0
            and quality_map.get("SUSPECT", 0) > 0
            and quality_map.get("INVALID", 0) > 0
        )

        print(
            "Quality categories are populated:",
            "PASSED" if quality_passed else "FAILED",
        )

        if not quality_passed:
            all_passed = False

        print("\n4. TIMESTAMP RANGE")

        minimum_timestamp = (
            session.query(func.min(TelemetryEvent.event_timestamp))
            .scalar()
        )

        maximum_timestamp = (
            session.query(func.max(TelemetryEvent.event_timestamp))
            .scalar()
        )

        print("First reading:", minimum_timestamp)
        print("Last reading: ", maximum_timestamp)

        timestamp_passed = (
            minimum_timestamp is not None
            and maximum_timestamp is not None
            and str(minimum_timestamp).startswith("2026-01-01")
            and str(maximum_timestamp).startswith("2026-03-31")
        )

        print(
            "90-day timestamp coverage:",
            "PASSED" if timestamp_passed else "FAILED",
        )

        if not timestamp_passed:
            all_passed = False

        print("\n5. FOREIGN KEY INTEGRITY")

        with engine.connect() as connection:
            foreign_key_errors = connection.exec_driver_sql(
                "PRAGMA foreign_key_check"
            ).fetchall()

        fk_passed = len(foreign_key_errors) == 0

        print(
            "Database foreign key check:",
            "PASSED" if fk_passed else "FAILED",
        )

        if not fk_passed:
            print(f"Foreign key errors: {foreign_key_errors[:10]}")
            all_passed = False

        print("\n6. OUTPUT FILES")

        expected_files = [
            "telemetry_events.csv.gz",
            "telemetry_events.jsonl.gz",
            "machine_state_history.csv",
            "machine_state_history.jsonl",
        ]

        for filename in expected_files:
            file_path = OUTPUT_DIR / filename
            exists = file_path.exists() and file_path.stat().st_size > 0

            print(
                f"{filename:35s}",
                "PASSED" if exists else "FAILED",
            )

            if not exists:
                all_passed = False

        print("\n" + "=" * 60)

        if all_passed:
            print("ALL TELEMETRY VALIDATION CHECKS PASSED!")
        else:
            print("SOME TELEMETRY VALIDATION CHECKS FAILED.")
            raise SystemExit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
