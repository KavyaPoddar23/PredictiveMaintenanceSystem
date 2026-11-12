
from datetime import datetime
from sqlalchemy import delete

from backend.app.database import SessionLocal
from backend.app.models import MaintenanceWorkOrder, MachineStateHistory


def repair_maintenance_state_history():
    db = SessionLocal()

    try:
        work_orders = (
            db.query(MaintenanceWorkOrder)
            .filter(
                MaintenanceWorkOrder.actual_start.isnot(None),
                MaintenanceWorkOrder.actual_end.isnot(None),
            )
            .order_by(MaintenanceWorkOrder.work_order_id)
            .all()
        )

        if not work_orders:
            raise RuntimeError(
                "No completed maintenance work orders found. "
                "Run Phase 5 maintenance generation first."
            )

        # Remove previously generated maintenance state events.
        db.execute(
            delete(MachineStateHistory).where(
                MachineStateHistory.state_event_id.like("MAINT-STATE-%")
            )
        )

        events = []

        for index, work_order in enumerate(work_orders, start=1):
            start_time = work_order.actual_start
            end_time = work_order.actual_end

            if end_time < start_time:
                raise ValueError(
                    f"Invalid maintenance timeline: {work_order.work_order_id}"
                )

            # Maintenance starts.
            events.append(
                MachineStateHistory(
                    state_event_id=f"MAINT-STATE-{index:06d}-001",
                    machine_id=work_order.machine_id,
                    previous_state="RUNNING",
                    new_state="MAINTENANCE",
                    changed_at=start_time,
                    reason=f"Maintenance started: {work_order.work_order_id}",
                )
            )

            # Maintenance completes.
            events.append(
                MachineStateHistory(
                    state_event_id=f"MAINT-STATE-{index:06d}-002",
                    machine_id=work_order.machine_id,
                    previous_state="MAINTENANCE",
                    new_state="RUNNING",
                    changed_at=end_time,
                    reason=f"Maintenance completed: {work_order.work_order_id}",
                )
            )

        db.add_all(events)
        db.commit()

        actual_count = (
            db.query(MachineStateHistory)
            .filter(
                MachineStateHistory.state_event_id.like("MAINT-STATE-%")
            )
            .count()
        )

        print(f"Completed work orders: {len(work_orders)}")
        print(f"Maintenance state events created: {actual_count}")

        if actual_count != len(work_orders) * 2:
            raise RuntimeError("Maintenance state event count is incorrect.")

        print("Maintenance state history repair successful.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    repair_maintenance_state_history()
