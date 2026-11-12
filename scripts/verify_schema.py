
from datetime import date

from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.app.database import Base, engine
from backend.app.models import Plant, ProductionLine


EXPECTED_TABLES = {
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
    "work_order_status_history",
}


def verify_tables():

    inspector = inspect(engine)

    actual_tables = set(inspector.get_table_names())

    missing = EXPECTED_TABLES - actual_tables

    print("\n1. DATABASE TABLE CHECK")

    if missing:
        print("FAILED. Missing tables:", missing)
        return False

    print(f"PASSED. All {len(EXPECTED_TABLES)} tables exist.")

    print("\n2. FOREIGN KEY CHECK")

    total_foreign_keys = 0

    for table in sorted(EXPECTED_TABLES):
        foreign_keys = inspector.get_foreign_keys(table)
        total_foreign_keys += len(foreign_keys)

        for fk in foreign_keys:
            print(
                f"{table}: "
                f"{fk['constrained_columns']} -> "
                f"{fk['referred_table']}"
            )

    print(f"\nTotal foreign key relationships: {total_foreign_keys}")

    with engine.connect() as connection:
        enabled = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar()

    if enabled != 1:
        print("FAILED. SQLite foreign keys are disabled.")
        return False

    print("PASSED. Foreign key enforcement is enabled.")

    return True


def verify_relationships():

    print("\n3. RELATIONSHIP INSERT CHECK")

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )

    @event.listens_for(test_engine, "connect")
    def enable_test_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)

    TestSession = sessionmaker(bind=test_engine)

    session = TestSession()

    try:
        plant = Plant(
            plant_id="PLT-TEST",
            name="Test Plant",
            location="Jaipur",
            timezone="Asia/Kolkata",
            status="ACTIVE"
        )

        line = ProductionLine(
            line_id="LINE-PLT-TEST-001",
            plant_id="PLT-TEST",
            name="Test Line",
            status="ACTIVE",
            effective_from=date(2026, 1, 1)
        )

        session.add(plant)
        session.add(line)
        session.commit()

        result = session.query(ProductionLine).first()

        assert result.plant.name == "Test Plant"
        assert len(plant.production_lines) == 1

        print("PASSED. Plant and ProductionLine relationship works.")

        print("\n4. INVALID FOREIGN KEY CHECK")

        invalid_line = ProductionLine(
            line_id="LINE-INVALID-001",
            plant_id="PLT-NONEXISTENT",
            name="Invalid Line",
            status="ACTIVE",
            effective_from=date(2026, 1, 1)
        )

        session.add(invalid_line)

        try:
            session.commit()

            print("FAILED. Invalid foreign key was accepted.")
            return False

        except IntegrityError:
            session.rollback()
            print("PASSED. Invalid foreign key was rejected.")

        return True

    finally:
        session.close()
        test_engine.dispose()


if __name__ == "__main__":

    print("=" * 55)
    print("DATABASE SCHEMA VERIFICATION")
    print("=" * 55)

    tables_ok = verify_tables()
    relationships_ok = verify_relationships()

    if tables_ok and relationships_ok:
        print("\nALL DATABASE CHECKS PASSED!")
    else:
        print("\nDATABASE VERIFICATION FAILED.")
        raise SystemExit(1)
