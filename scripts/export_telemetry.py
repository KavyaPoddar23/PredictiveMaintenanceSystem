
import csv
import gzip
import io
import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import TelemetryEvent


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "telemetry"

CSV_PATH = OUTPUT_DIR / "telemetry_events.csv.gz"
JSONL_PATH = OUTPUT_DIR / "telemetry_events.jsonl.gz"

BATCH_SIZE = 10000

FIELDS = [
    "telemetry_id",
    "sensor_id",
    "event_timestamp",
    "value",
    "unit",
    "operating_state",
    "quality_status",
    "issue_type",
]


def deterministic_gzip_text(path):
    """
    Create a gzip text stream with a fixed timestamp and filename.
    This makes compressed output reproducible.
    """
    raw_file = open(path, "wb")

    gzip_file = gzip.GzipFile(
        filename="",
        mode="wb",
        fileobj=raw_file,
        compresslevel=9,
        mtime=0,
    )

    text_file = io.TextIOWrapper(
        gzip_file,
        encoding="utf-8",
        newline="",
    )

    return text_file, raw_file


def export_telemetry(db: Session):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    query = (
        db.query(TelemetryEvent)
        .order_by(
            TelemetryEvent.event_timestamp,
            TelemetryEvent.sensor_id,
        )
        .yield_per(BATCH_SIZE)
    )

    total = 0

    csv_text, csv_raw = deterministic_gzip_text(CSV_PATH)
    jsonl_text, jsonl_raw = deterministic_gzip_text(JSONL_PATH)

    try:
        writer = csv.DictWriter(
            csv_text,
            fieldnames=FIELDS,
        )

        writer.writeheader()

        for event in query:
            record = {
                "telemetry_id": event.telemetry_id,
                "sensor_id": event.sensor_id,
                "event_timestamp": (
                    event.event_timestamp.isoformat()
                    if event.event_timestamp
                    else None
                ),
                "value": event.value,
                "unit": event.unit,
                "operating_state": event.operating_state,
                "quality_status": event.quality_status,
                "issue_type": event.issue_type,
            }

            writer.writerow(record)

            jsonl_text.write(
                json.dumps(
                    record,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ) + "\n"
            )

            total += 1

            if total % 100000 == 0:
                print(f"Exported {total:,} telemetry records")

    finally:
        csv_text.close()
        jsonl_text.close()
        csv_raw.close()
        jsonl_raw.close()

    print("\nDeterministic telemetry export completed.")
    print(f"Total records: {total:,}")
    print(f"CSV: {CSV_PATH}")
    print(f"JSONL: {JSONL_PATH}")

    return total


def main():
    db = SessionLocal()

    try:
        total = export_telemetry(db)

        if total == 0:
            raise RuntimeError(
                "No telemetry records found in database."
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
