
import csv
from pathlib import Path

from sqlalchemy import func

from backend.app.database import SessionLocal
from backend.app.models import (
    Machine,
    MaintenanceWorkOrder,
    FailureEvent,
    WorkOrderPart,
    WorkOrderTechnician,
    WorkOrderStatusHistory,
    MachineStateHistory,
    Part,
)


BASE_DIR = Path(__file__).resolve().parents[1]

GROUND_TRUTH_FILE = (
    BASE_DIR / "data" / "ground_truth" / "failure_labels.csv"
)

MASTER_PARTS_FILE = (
    BASE_DIR / "data" / "master" / "parts.csv"
)

EXPECTED_FAILURES = 120


def main():
    session = SessionLocal()
    all_passed = True

    try:
        print("=" * 60)
        print("MAINTENANCE DATA VALIDATION")
        print("=" * 60)

        # -------------------------------------------------
        # 1. RECORD COUNTS
        # -------------------------------------------------

        print("\n1. RECORD COUNTS")

        checks = [
            (
                "Machines",
                session.query(Machine).count(),
                100,
            ),
            (
                "Maintenance work orders",
                session.query(MaintenanceWorkOrder).count(),
                EXPECTED_FAILURES,
            ),
            (
                "Failure events",
                session.query(FailureEvent).count(),
                EXPECTED_FAILURES,
            ),
            (
                "Part usage records",
                session.query(WorkOrderPart).count(),
                None,
            ),
            (
                "Technician assignments",
                session.query(WorkOrderTechnician).count(),
                None,
            ),
            (
                "Work-order status events",
                session.query(WorkOrderStatusHistory).count(),
                EXPECTED_FAILURES * 3,
            ),
        ]

        for label, actual, expected in checks:
            passed = expected is None or actual == expected

            expected_text = (
                "Generated" if expected is None
                else f"{expected:,}"
            )

            print(
                f"{label:30s} "
                f"Expected: {expected_text:>10s} "
                f"Actual: {actual:>10,} "
                f"{'PASSED' if passed else 'FAILED'}"
            )

            if not passed:
                all_passed = False

        # -------------------------------------------------
        # 2. FAILURE AND WORK ORDER RELATIONSHIPS
        # -------------------------------------------------

        print("\n2. FAILURE AND WORK ORDER LINKS")

        failures = session.query(FailureEvent).all()

        links_passed = (
            len(failures) == EXPECTED_FAILURES
            and all(
                failure.work_order_id is not None
                and failure.work_order is not None
                and failure.work_order.machine_id == failure.machine_id
                for failure in failures
            )
        )

        print(
            "Every failure has a matching work order:",
            "PASSED" if links_passed else "FAILED",
        )

        if not links_passed:
            all_passed = False

        # -------------------------------------------------
        # 3. DATE VALIDATION
        # -------------------------------------------------

        print("\n3. TIMELINE VALIDATION")

        date_passed = all(
            failure.symptom_first_observed_at < failure.occurred_at
            and failure.downtime_end >= failure.downtime_start
            for failure in failures
        )

        print(
            "Symptoms precede failures and downtime dates are valid:",
            "PASSED" if date_passed else "FAILED",
        )

        if not date_passed:
            all_passed = False

        # -------------------------------------------------
        # 4. WORK ORDER LIFECYCLE
        # -------------------------------------------------

        print("\n4. WORK ORDER LIFECYCLE")

        completed_orders = (
            session.query(MaintenanceWorkOrder)
            .filter(
                MaintenanceWorkOrder.status == "COMPLETED"
            )
            .count()
        )

        lifecycle_passed = (
            completed_orders == EXPECTED_FAILURES
        )

        print(
            "All generated work orders are completed:",
            "PASSED" if lifecycle_passed else "FAILED",
        )

        if not lifecycle_passed:
            all_passed = False

        # -------------------------------------------------
        # 5. STATUS HISTORY
        # -------------------------------------------------

        print("\n5. STATUS HISTORY")

        status_events = (
            session.query(WorkOrderStatusHistory).count()
        )

        status_passed = (
            status_events == EXPECTED_FAILURES * 3
        )

        print(
            "Three status events per work order:",
            "PASSED" if status_passed else "FAILED",
        )

        if not status_passed:
            all_passed = False

        # -------------------------------------------------
        # 6. PART USAGE
        # -------------------------------------------------

        print("\n6. PART USAGE")

        invalid_part_usage = (
            session.query(WorkOrderPart)
            .filter(
                (WorkOrderPart.quantity <= 0)
                | (WorkOrderPart.unit_cost_at_use < 0)
            )
            .count()
        )

        part_usage_passed = (
            invalid_part_usage == 0
            and session.query(WorkOrderPart).count() > 0
        )

        print(
            "Part quantities and costs are valid:",
            "PASSED" if part_usage_passed else "FAILED",
        )

        if not part_usage_passed:
            all_passed = False

        # -------------------------------------------------
        # 7. INVENTORY RECONCILIATION
        # -------------------------------------------------

        print("\n7. INVENTORY RECONCILIATION")

        with MASTER_PARTS_FILE.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            baseline_parts = list(csv.DictReader(file))

        inventory_passed = True

        for baseline in baseline_parts:
            part_id = baseline["part_id"]
            initial_stock = int(baseline["stock_quantity"])

            used = (
                session.query(
                    func.coalesce(func.sum(WorkOrderPart.quantity), 0)
                )
                .filter(WorkOrderPart.part_id == part_id)
                .scalar()
            )

            current_part = session.get(Part, part_id)

            if current_part is None:
                inventory_passed = False
                break

            expected_remaining = initial_stock - used

            if current_part.stock_quantity != expected_remaining:
                inventory_passed = False
                break

        print(
            "Opening stock - parts used = remaining stock:",
            "PASSED" if inventory_passed else "FAILED",
        )

        if not inventory_passed:
            all_passed = False

        # -------------------------------------------------
        # 8. GROUND TRUTH SEPARATION
        # -------------------------------------------------

        print("\n8. GROUND TRUTH SEPARATION")

        ground_truth_passed = False

        if GROUND_TRUTH_FILE.exists():
            with GROUND_TRUTH_FILE.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as file:
                labels = list(csv.DictReader(file))

            ground_truth_passed = (
                len(labels) == EXPECTED_FAILURES
                and all(
                    label["failure_occurred"] == "1"
                    for label in labels
                )
            )

        print(
            "120 labels stored in separate ground-truth file:",
            "PASSED" if ground_truth_passed else "FAILED",
        )

        if not ground_truth_passed:
            all_passed = False

        # -------------------------------------------------
        # 9. MACHINE STATE HISTORY
        # -------------------------------------------------

        print("\n9. MACHINE STATE HISTORY")

        maintenance_state_events = (
            session.query(MachineStateHistory)
            .filter(
                MachineStateHistory.state_event_id.like(
                    "MAINT-STATE-%"
                )
            )
            .count()
        )

        state_passed = (
            maintenance_state_events == EXPECTED_FAILURES * 2
        )

        print(
            "Maintenance start and completion events:",
            "PASSED" if state_passed else "FAILED",
        )

        if not state_passed:
            all_passed = False

        # -------------------------------------------------
        # FINAL RESULT
        # -------------------------------------------------

        print("\n" + "=" * 60)

        if all_passed:
            print("ALL MAINTENANCE VALIDATION CHECKS PASSED!")
        else:
            print("SOME MAINTENANCE VALIDATION CHECKS FAILED.")
            raise SystemExit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
