
from backend.app.database import Base, engine

# Importing models registers all tables with SQLAlchemy
from backend.app.models import (
    Plant,
    ProductionLine,
    Machine,
    Sensor,
    TelemetryEvent,
    OperatingShift,
    MaintenanceWorkOrder,
    FailureEvent,
    Part,
    Technician,
    WorkOrderPart,
    WorkOrderTechnician,
    MachineStateHistory,
    WorkOrderStatusHistory,
)

from sqlalchemy import inspect


def initialize_database():

    print("Initializing industrial maintenance database...")

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Inspect created tables
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    print("\nDatabase created successfully!")
    print(f"Database location: {engine.url.database}")

    print("\nCreated tables:")

    for table in tables:
        print(f" - {table}")

    print(f"\nTotal tables created: {len(tables)}")


if __name__ == "__main__":
    initialize_database()
