
import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "industrial_maintenance.db"
REPORT_DIR = ROOT / "data" / "validation_reports"

EXPECTED_COUNTS = {
    "plants": 3,
    "production_lines": 12,
    "machines": 100,
    "sensors": 500,
    "operating_shifts": 9,
    "telemetry_events": 2160000,
    "maintenance_work_orders": 120,
    "failure_events": 120,
    "parts": 25,
    "technicians": 30,
}

EXPECTED_TELEMETRY_PER_SENSOR = 4320

checks = []


def record_check(name, passed, details=""):
    checks.append({
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "details": str(details),
    })

    symbol = "PASS" if passed else "FAIL"
    print(f"[{symbol}] {name}")

    if details:
        print(f"       {details}")


def connect_database():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def table_exists(connection, table_name):
    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return result[0] == 1


def scalar(connection, query, params=()):
    result = connection.execute(query, params).fetchone()
    return result[0] if result else None


def validate_tables(connection):
    print("\n--- TABLE VALIDATION ---")

    required_tables = list(EXPECTED_COUNTS.keys()) + [
        "work_order_parts",
        "work_order_technicians",
        "machine_state_history",
        "work_order_status_history",
    ]

    for table in required_tables:
        exists = table_exists(connection, table)
        record_check(
            f"Table exists: {table}",
            exists,
        )


def validate_record_counts(connection):
    print("\n--- RECORD COUNT VALIDATION ---")

    for table, expected in EXPECTED_COUNTS.items():
        if not table_exists(connection, table):
            record_check(
                f"Record count: {table}",
                False,
                "Table does not exist",
            )
            continue

        actual = scalar(
            connection,
            f"SELECT COUNT(*) FROM {table}",
        )

        record_check(
            f"Record count: {table}",
            actual == expected,
            f"Expected={expected:,}, Actual={actual:,}",
        )


def validate_primary_keys(connection):
    print("\n--- PRIMARY KEY VALIDATION ---")

    primary_keys = {
        "plants": "plant_id",
        "production_lines": "line_id",
        "machines": "machine_id",
        "sensors": "sensor_id",
        "telemetry_events": "telemetry_id",
        "operating_shifts": "shift_id",
        "maintenance_work_orders": "work_order_id",
        "failure_events": "failure_event_id",
        "parts": "part_id",
        "technicians": "technician_id",
        "machine_state_history": "state_event_id",
        "work_order_status_history": "status_event_id",
    }

    for table, column in primary_keys.items():
        if not table_exists(connection, table):
            continue

        null_count = scalar(
            connection,
            f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL",
        )

        duplicate_count = scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT {column}
                FROM {table}
                GROUP BY {column}
                HAVING COUNT(*) > 1
            )
            """,
        )

        record_check(
            f"Primary key integrity: {table}",
            null_count == 0 and duplicate_count == 0,
            f"Nulls={null_count}, Duplicate groups={duplicate_count}",
        )


def validate_foreign_keys(connection):
    print("\n--- FOREIGN KEY VALIDATION ---")

    result = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    record_check(
        "Foreign key integrity",
        len(result) == 0,
        f"Violations={len(result)}",
    )


def validate_custom_relationships(connection):
    print("\n--- RELATIONSHIP VALIDATION ---")

    checks_to_run = [
        (
            "Production lines reference valid plants",
            """
            SELECT COUNT(*)
            FROM production_lines p
            LEFT JOIN plants pl ON p.plant_id = pl.plant_id
            WHERE pl.plant_id IS NULL
            """,
        ),
        (
            "Machines reference valid production lines",
            """
            SELECT COUNT(*)
            FROM machines m
            LEFT JOIN production_lines p ON m.line_id = p.line_id
            WHERE p.line_id IS NULL
            """,
        ),
        (
            "Sensors reference valid machines",
            """
            SELECT COUNT(*)
            FROM sensors s
            LEFT JOIN machines m ON s.machine_id = m.machine_id
            WHERE m.machine_id IS NULL
            """,
        ),
        (
            "Telemetry references valid sensors",
            """
            SELECT COUNT(*)
            FROM telemetry_events t
            LEFT JOIN sensors s ON t.sensor_id = s.sensor_id
            WHERE s.sensor_id IS NULL
            """,
        ),
        (
            "Work orders reference valid machines",
            """
            SELECT COUNT(*)
            FROM maintenance_work_orders w
            LEFT JOIN machines m ON w.machine_id = m.machine_id
            WHERE m.machine_id IS NULL
            """,
        ),
        (
            "Failures reference valid machines",
            """
            SELECT COUNT(*)
            FROM failure_events f
            LEFT JOIN machines m ON f.machine_id = m.machine_id
            WHERE m.machine_id IS NULL
            """,
        ),
    ]

    for name, query in checks_to_run:
        count = scalar(connection, query)

        record_check(
            name,
            count == 0,
            f"Invalid relationships={count}",
        )


def validate_telemetry(connection):
    print("\n--- TELEMETRY VALIDATION ---")

    duplicate_groups = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT sensor_id, event_timestamp
            FROM telemetry_events
            GROUP BY sensor_id, event_timestamp
            HAVING COUNT(*) > 1
        )
        """,
    )

    record_check(
        "No duplicate sensor timestamp pairs",
        duplicate_groups == 0,
        f"Duplicate groups={duplicate_groups}",
    )

    incomplete_sensors = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT s.sensor_id, COUNT(t.telemetry_id) AS reading_count
            FROM sensors s
            LEFT JOIN telemetry_events t
                ON s.sensor_id = t.sensor_id
            GROUP BY s.sensor_id
            HAVING reading_count != ?
        )
        """,
        (EXPECTED_TELEMETRY_PER_SENSOR,),
    )

    record_check(
        "Each sensor has expected telemetry coverage",
        incomplete_sensors == 0,
        f"Sensors with unexpected reading counts={incomplete_sensors}",
    )

    invalid_units = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM telemetry_events t
        JOIN sensors s ON t.sensor_id = s.sensor_id
        WHERE t.unit != s.unit
        """,
    )

    record_check(
        "Telemetry units match sensor units",
        invalid_units == 0,
        f"Unit mismatches={invalid_units}",
    )

    invalid_quality = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM telemetry_events
        WHERE quality_status NOT IN ('VALID', 'SUSPECT', 'INVALID')
        """,
    )

    record_check(
        "Telemetry quality values are valid",
        invalid_quality == 0,
        f"Invalid quality values={invalid_quality}",
    )

    unmarked_out_of_range = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM telemetry_events t
        JOIN sensors s ON t.sensor_id = s.sensor_id
        WHERE (
            t.value < s.min_valid
            OR t.value > s.max_valid
        )
        AND t.quality_status != 'INVALID'
        """,
    )

    record_check(
        "Out-of-range readings are marked INVALID",
        unmarked_out_of_range == 0,
        f"Unmarked out-of-range readings={unmarked_out_of_range}",
    )

    invalid_fault_markers = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM telemetry_events
        WHERE quality_status = 'VALID'
          AND issue_type IS NOT NULL
        """,
    )

    record_check(
        "Valid telemetry has no fault issue marker",
        invalid_fault_markers == 0,
        f"Contradictory records={invalid_fault_markers}",
    )

    missing_values = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM telemetry_events
        WHERE value IS NULL OR event_timestamp IS NULL
        """,
    )

    record_check(
        "Telemetry has timestamp and value",
        missing_values == 0,
        f"Missing records={missing_values}",
    )


def validate_maintenance(connection):
    print("\n--- MAINTENANCE VALIDATION ---")

    invalid_timelines = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM maintenance_work_orders
        WHERE
            (
                actual_start IS NOT NULL
                AND actual_end IS NOT NULL
                AND actual_end < actual_start
            )
            OR
            (
                actual_start IS NOT NULL
                AND opened_at IS NOT NULL
                AND actual_start < opened_at
            )
        """,
    )

    record_check(
        "Maintenance work order timelines are valid",
        invalid_timelines == 0,
        f"Invalid timelines={invalid_timelines}",
    )

    mismatched_failures = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM failure_events f
        JOIN maintenance_work_orders w
            ON f.work_order_id = w.work_order_id
        WHERE f.machine_id != w.machine_id
        """,
    )

    record_check(
        "Failure and work order machine IDs match",
        mismatched_failures == 0,
        f"Mismatches={mismatched_failures}",
    )

    invalid_downtime = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM failure_events
        WHERE downtime_start IS NOT NULL
          AND downtime_end IS NOT NULL
          AND downtime_end < downtime_start
        """,
    )

    record_check(
        "Failure downtime timelines are valid",
        invalid_downtime == 0,
        f"Invalid downtime records={invalid_downtime}",
    )

    status_history = scalar(
        connection,
        "SELECT COUNT(*) FROM work_order_status_history",
    )

    record_check(
        "Work order status history exists",
        status_history > 0,
        f"Status events={status_history}",
    )

    maintenance_events = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM machine_state_history
        WHERE state_event_id LIKE 'MAINT-STATE-%'
        """,
    )

    completed_orders = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM maintenance_work_orders
        WHERE actual_start IS NOT NULL
          AND actual_end IS NOT NULL
        """,
    )

    expected_events = completed_orders * 2

    record_check(
        "Machine state history has start and completion events",
        maintenance_events == expected_events,
        (
            f"Expected={expected_events}, "
            f"Actual={maintenance_events}"
        ),
    )


def validate_parts(connection):
    print("\n--- PARTS VALIDATION ---")

    negative_stock = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM parts
        WHERE stock_quantity < 0
        """,
    )

    record_check(
        "Parts inventory is non-negative",
        negative_stock == 0,
        f"Parts with negative stock={negative_stock}",
    )

    invalid_usage = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM work_order_parts
        WHERE quantity <= 0 OR unit_cost_at_use < 0
        """,
    )

    record_check(
        "Work order part usage values are valid",
        invalid_usage == 0,
        f"Invalid usage records={invalid_usage}",
    )


def validate_inventory_reconciliation(connection):
    print("\n--- INVENTORY RECONCILIATION ---")

    parts_file = ROOT / "data" / "master" / "parts.csv"

    if not parts_file.exists():
        record_check(
            "Parts inventory reconciliation",
            False,
            "data/master/parts.csv is missing",
        )
        return

    mismatches = []

    with open(parts_file, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for part in reader:
            part_id = part["part_id"]
            opening_stock = int(part["stock_quantity"])

            used = scalar(
                connection,
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM work_order_parts
                WHERE part_id = ?
                """,
                (part_id,),
            )

            current = scalar(
                connection,
                """
                SELECT stock_quantity
                FROM parts
                WHERE part_id = ?
                """,
                (part_id,),
            )

            if current is None:
                mismatches.append(part_id)
                continue

            expected = opening_stock - used

            if current != expected:
                mismatches.append(part_id)

    record_check(
        "Parts inventory reconciles with work order usage",
        len(mismatches) == 0,
        f"Mismatched parts={len(mismatches)}",
    )


def validate_ground_truth():
    print("\n--- GROUND TRUTH VALIDATION ---")

    label_file = ROOT / "data" / "ground_truth" / "failure_labels.csv"

    record_check(
        "Ground truth label file exists",
        label_file.exists(),
        str(label_file),
    )

    if not label_file.exists():
        return

    with open(label_file, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    record_check(
        "Ground truth labels are not empty",
        len(rows) > 0,
        f"Label rows={len(rows)}",
    )


def validate_output_files():
    print("\n--- OUTPUT FILE VALIDATION ---")

    required_files = [
        "data/master/plants.csv",
        "data/master/production_lines.csv",
        "data/master/machines.csv",
        "data/master/sensors.csv",
        "data/master/operating_shifts.csv",
        "data/master/parts.csv",
        "data/master/technicians.csv",
        "data/telemetry/telemetry_events.csv.gz",
        "data/telemetry/telemetry_events.jsonl.gz",
        "data/transactions/maintenance_work_orders.csv",
        "data/transactions/failure_events.csv",
        "data/ground_truth/failure_labels.csv",
    ]

    for relative_path in required_files:
        path = ROOT / relative_path

        record_check(
            f"Output file exists: {relative_path}",
            path.exists() and path.stat().st_size > 0,
        )


def calculate_checksums():
    print("\n--- CHECKSUM GENERATION ---")

    directories = [
        ROOT / "data" / "master",
        ROOT / "data" / "telemetry",
        ROOT / "data" / "transactions",
        ROOT / "data" / "ground_truth",
    ]

    checksums = {}

    for directory in directories:
        if not directory.exists():
            continue

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue

            digest = hashlib.sha256()

            with open(path, "rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)

            relative = str(path.relative_to(ROOT)).replace("\\", "/")
            checksums[relative] = digest.hexdigest()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    checksum_path = REPORT_DIR / "checksums.json"

    with open(checksum_path, "w", encoding="utf-8") as file:
        json.dump(checksums, file, indent=4)

    record_check(
        "SHA-256 checksums generated",
        len(checksums) > 0,
        f"Files hashed={len(checksums)}",
    )


def save_reports():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "total_checks": len(checks),
        "passed": sum(c["status"] == "PASS" for c in checks),
        "failed": sum(c["status"] == "FAIL" for c in checks),
        "overall_status": (
            "PASS"
            if all(c["status"] == "PASS" for c in checks)
            else "FAIL"
        ),
        "checks": checks,
    }

    with open(
        REPORT_DIR / "validation_summary.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(summary, file, indent=4)

    with open(
        REPORT_DIR / "validation_details.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["check", "status", "details"],
        )
        writer.writeheader()
        writer.writerows(checks)

    print("\n--- VALIDATION SUMMARY ---")
    print(f"Total checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Overall status: {summary['overall_status']}")


def main():
    checks.clear()

    print("=" * 60)
    print("INDUSTRIAL PREDICTIVE MAINTENANCE DATA VALIDATION")
    print("=" * 60)

    connection = connect_database()

    try:
        validate_tables(connection)
        validate_record_counts(connection)
        validate_primary_keys(connection)
        validate_foreign_keys(connection)
        validate_custom_relationships(connection)
        validate_telemetry(connection)
        validate_maintenance(connection)
        validate_parts(connection)
        validate_inventory_reconciliation(connection)

    finally:
        connection.close()

    validate_ground_truth()
    validate_output_files()
    calculate_checksums()
    save_reports()

    failed = [
        item for item in checks
        if item["status"] == "FAIL"
    ]

    if failed:
        raise SystemExit(
            "\nSome validation checks failed. "
            "Review data/validation_reports/validation_details.csv"
        )

    print("\nAll validation checks passed successfully.")


if __name__ == "__main__":
    main()
