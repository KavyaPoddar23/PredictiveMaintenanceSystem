
import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "industrial_maintenance.db"


@pytest.fixture
def connection():
    if not DB_PATH.exists():
        pytest.skip("Generated database is not available.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()


def test_required_tables_exist(connection):
    required_tables = {
        "plants",
        "production_lines",
        "machines",
        "sensors",
        "telemetry_events",
        "operating_shifts",
        "maintenance_work_orders",
        "failure_events",
        "parts",
        "technicians",
        "work_order_parts",
        "work_order_technicians",
        "machine_state_history",
        "work_order_status_history"
    }

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    actual_tables = {row["name"] for row in rows}

    missing = required_tables - actual_tables

    assert not missing, f"Missing database tables: {missing}"


def test_primary_ids_are_unique(connection):
    checks = [
        ("plants", "plant_id"),
        ("production_lines", "line_id"),
        ("machines", "machine_id"),
        ("sensors", "sensor_id"),
        ("telemetry_events", "telemetry_id"),
        ("maintenance_work_orders", "work_order_id"),
        ("failure_events", "failure_event_id")
    ]

    for table, column in checks:
        duplicate_count = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM (
                SELECT {column}
                FROM {table}
                GROUP BY {column}
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()["total"]

        assert duplicate_count == 0, (
            f"Duplicate IDs found in {table}.{column}"
        )


def test_foreign_key_integrity(connection):
    violations = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    assert len(violations) == 0, (
        f"Foreign key violations found: {violations[:10]}"
    )


def test_required_master_data_counts(connection):
    expected_counts = {
        "plants": 3,
        "production_lines": 12,
        "machines": 100,
        "sensors": 500,
        "operating_shifts": 9,
        "parts": 25,
        "technicians": 30
    }

    for table, expected in expected_counts.items():
        actual = connection.execute(
            f"SELECT COUNT(*) AS total FROM {table}"
        ).fetchone()["total"]

        assert actual == expected, (
            f"{table}: expected {expected}, found {actual}"
        )


def test_telemetry_coverage(connection):
    sensor_count = connection.execute(
        "SELECT COUNT(*) FROM sensors"
    ).fetchone()[0]

    sensors_with_expected_coverage = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT sensor_id, COUNT(*) AS reading_count
            FROM telemetry_events
            GROUP BY sensor_id
            HAVING reading_count = 4320
        )
        """
    ).fetchone()[0]

    assert sensor_count == 500
    assert sensors_with_expected_coverage == sensor_count


def test_no_orphaned_telemetry(connection):
    orphan_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM telemetry_events t
        LEFT JOIN sensors s
            ON t.sensor_id = s.sensor_id
        WHERE s.sensor_id IS NULL
        """
    ).fetchone()[0]

    assert orphan_count == 0


def test_failure_records_have_valid_machines(connection):
    invalid_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM failure_events f
        LEFT JOIN machines m
            ON f.machine_id = m.machine_id
        WHERE m.machine_id IS NULL
        """
    ).fetchone()[0]

    assert invalid_count == 0


def test_work_order_dates_are_valid(connection):
    invalid_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM maintenance_work_orders
        WHERE actual_start IS NOT NULL
          AND actual_end IS NOT NULL
          AND julianday(actual_end) < julianday(actual_start)
        """
    ).fetchone()[0]

    assert invalid_count == 0
