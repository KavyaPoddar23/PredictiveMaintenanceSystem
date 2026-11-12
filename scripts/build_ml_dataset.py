
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "industrial_maintenance.db"
OUTPUT_DIR = ROOT / "data" / "features"

FEATURES_PATH = OUTPUT_DIR / "machine_features.csv"
LABELS_PATH = OUTPUT_DIR / "machine_labels.csv"
METADATA_PATH = OUTPUT_DIR / "feature_metadata.json"

START_TIME = datetime(2026, 1, 1, 0, 0, 0)

# The generated telemetry covers 90 days.
DATA_END = START_TIME + timedelta(days=90)

BUCKET_HOURS = 6
BUCKET_SECONDS = BUCKET_HOURS * 60 * 60
BUCKET_COUNT = 360

LOOKBACK_BUCKETS = 4
PREDICTION_HOURS = 24

# Keep the prediction horizon inside the telemetry period.
FIRST_SNAPSHOT_BUCKET = LOOKBACK_BUCKETS
LAST_SNAPSHOT_BUCKET = (
    BUCKET_COUNT - PREDICTION_HOURS // BUCKET_HOURS
)

SNAPSHOT_BUCKETS = range(
    FIRST_SNAPSHOT_BUCKET,
    LAST_SNAPSHOT_BUCKET + 1,
)


def connect_database():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def load_machine_metadata(connection):
    rows = connection.execute(
        """
        SELECT machine_id, criticality
        FROM machines
        ORDER BY machine_id
        """
    ).fetchall()

    if not rows:
        raise RuntimeError("No machines found.")

    criticality_mapping = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    result = {}

    for row in rows:
        criticality = str(row["criticality"]).upper()

        result[row["machine_id"]] = {
            "criticality_numeric": criticality_mapping.get(
                criticality, 0
            )
        }

    return result


def load_sensor_bucket_aggregates(connection):
    print("Aggregating telemetry into six-hour buckets...")

    query = """
        SELECT
            m.machine_id,
            s.sensor_type,

            CAST(
                (
                    (
                        julianday(t.event_timestamp)
                        - julianday(?)
                    ) * 4
                ) + 0.000001
                AS INTEGER
            ) AS bucket_id,

            COUNT(*) AS reading_count,

            AVG(
                CASE
                    WHEN t.quality_status = 'VALID'
                    THEN t.value
                END
            ) AS valid_mean,

            MIN(t.value) AS bucket_min,
            MAX(t.value) AS bucket_max,

            SUM(
                CASE
                    WHEN t.quality_status = 'INVALID'
                    THEN 1 ELSE 0
                END
            ) AS invalid_count,

            SUM(
                CASE
                    WHEN t.quality_status = 'SUSPECT'
                    THEN 1 ELSE 0
                END
            ) AS suspect_count

        FROM telemetry_events t

        JOIN sensors s
            ON t.sensor_id = s.sensor_id

        JOIN machines m
            ON s.machine_id = m.machine_id

        WHERE julianday(t.event_timestamp) >= julianday(?)
  AND julianday(t.event_timestamp) < julianday(?)

        GROUP BY
            m.machine_id,
            s.sensor_type,
            bucket_id

        ORDER BY
            m.machine_id,
            s.sensor_type,
            bucket_id
    """

    rows = connection.execute(
        query,
        (
            START_TIME.isoformat(),
            START_TIME.isoformat(),
            DATA_END.isoformat(),
        ),
    ).fetchall()

    result = defaultdict(dict)

    for row in rows:
        bucket_id = row["bucket_id"]

        if bucket_id is None or not (
            0 <= bucket_id < BUCKET_COUNT
        ):
            continue

        result[row["machine_id"]].setdefault(
            row["sensor_type"], {}
        )[bucket_id] = {
            "reading_count": row["reading_count"],
            "valid_mean": row["valid_mean"],
            "bucket_min": row["bucket_min"],
            "bucket_max": row["bucket_max"],
            "invalid_count": row["invalid_count"],
            "suspect_count": row["suspect_count"],
        }

    print(f"Machines with telemetry: {len(result)}")

    return result


def load_operating_state_aggregates(connection):
    print("Aggregating operating states...")

    query = """
        SELECT
            m.machine_id,

            CAST(
                (
                    (
                        julianday(t.event_timestamp)
                        - julianday(?)
                    ) * 4
                ) + 0.000001
                AS INTEGER
            ) AS bucket_id,

            t.operating_state,
            COUNT(*) AS state_count

        FROM telemetry_events t

        JOIN sensors s
            ON t.sensor_id = s.sensor_id

        JOIN machines m
            ON s.machine_id = m.machine_id

        WHERE t.event_timestamp >= ?
          AND t.event_timestamp < ?

        GROUP BY
            m.machine_id,
            bucket_id,
            t.operating_state
    """

    rows = connection.execute(
        query,
        (
            START_TIME.isoformat(),
            START_TIME.isoformat(),
            DATA_END.isoformat(),
        ),
    ).fetchall()

    result = defaultdict(dict)

    for row in rows:
        bucket_id = row["bucket_id"]

        if bucket_id is None or not (
            0 <= bucket_id < BUCKET_COUNT
        ):
            continue

        state = str(
            row["operating_state"] or "UNKNOWN"
        ).upper()

        result[row["machine_id"]].setdefault(
            bucket_id, {}
        )[state] = row["state_count"]

    return result


def load_failure_events(connection):
    print("Loading failure timestamps for labels...")

    rows = connection.execute(
        """
        SELECT machine_id, occurred_at
        FROM failure_events
        ORDER BY machine_id, occurred_at
        """
    ).fetchall()

    result = defaultdict(list)

    for row in rows:
        if not row["occurred_at"]:
            continue

        failure_time = pd.Timestamp(
            row["occurred_at"]
        ).to_pydatetime()

        result[row["machine_id"]].append(failure_time)

    return result


def rolling_features_for_machine(
    machine_id,
    sensor_data,
    state_data,
    metadata,
):
    grid = pd.DataFrame(
        index=range(BUCKET_COUNT)
    )

    sensor_types = sorted(
        sensor_data.get(machine_id, {}).keys()
    )

    for sensor_type in sensor_types:
        bucket_records = sensor_data[machine_id][sensor_type]

        bucket_frame = pd.DataFrame.from_dict(
            bucket_records,
            orient="index",
        ).reindex(range(BUCKET_COUNT))

        prefix = str(sensor_type).upper().replace(" ", "_")

        rolling_mean = (
            bucket_frame["valid_mean"]
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .mean()
            .shift(1)
        )

        rolling_std = (
            bucket_frame["valid_mean"]
            .rolling(LOOKBACK_BUCKETS, min_periods=2)
            .std()
            .shift(1)
        )

        rolling_min = (
            bucket_frame["bucket_min"]
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .min()
            .shift(1)
        )

        rolling_max = (
            bucket_frame["bucket_max"]
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .max()
            .shift(1)
        )

        rolling_count = (
            bucket_frame["reading_count"]
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .sum()
            .shift(1)
        )

        rolling_invalid = (
            bucket_frame["invalid_count"]
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .sum()
            .shift(1)
        )

        rolling_suspect = (
            bucket_frame["suspect_count"]
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .sum()
            .shift(1)
        )

        grid[f"{prefix}_mean_24h"] = rolling_mean
        grid[f"{prefix}_std_24h"] = rolling_std
        grid[f"{prefix}_min_24h"] = rolling_min
        grid[f"{prefix}_max_24h"] = rolling_max
        grid[f"{prefix}_reading_count_24h"] = rolling_count

        grid[f"{prefix}_invalid_rate_24h"] = (
            rolling_invalid / rolling_count.replace(0, float("nan"))
        )

        grid[f"{prefix}_suspect_rate_24h"] = (
            rolling_suspect / rolling_count.replace(0, float("nan"))
        )

    # Operating-state distribution over the previous 24 hours.
    states = state_data.get(machine_id, {})

    all_states = sorted({
        state
        for bucket in states.values()
        for state in bucket
    })

    state_frame = pd.DataFrame(
        index=range(BUCKET_COUNT)
    )

    for state in all_states:
        state_counts = pd.Series(
            {
                bucket_id: counts.get(state, 0)
                for bucket_id, counts in states.items()
            },
            dtype="float64",
        ).reindex(range(BUCKET_COUNT), fill_value=0)

        rolling_state_count = (
            state_counts
            .rolling(LOOKBACK_BUCKETS, min_periods=1)
            .sum()
            .shift(1)
        )

        state_frame[
            f"state_{state.lower()}_count_24h"
        ] = rolling_state_count

    if not state_frame.empty:
        total_state_count = state_frame.sum(axis=1)

        for column in list(state_frame.columns):
            percentage_column = column.replace(
                "_count_24h", "_percentage_24h"
            )

            grid[percentage_column] = (
                state_frame[column]
                / total_state_count.replace(0, float("nan"))
            )

    grid["criticality_numeric"] = metadata[
        machine_id
    ]["criticality_numeric"]

    return grid


def create_snapshot_rows(
    machine_metadata,
    sensor_data,
    state_data,
    failure_events,
):
    feature_rows = []
    label_rows = []

    machine_ids = sorted(machine_metadata)

    for machine_number, machine_id in enumerate(
        machine_ids, start=1
    ):
        print(
            f"Processing machine {machine_number}/"
            f"{len(machine_ids)}: {machine_id}"
        )

        grid = rolling_features_for_machine(
            machine_id,
            sensor_data,
            state_data,
            machine_metadata,
        )

        machine_failures = sorted(
            failure_events.get(machine_id, [])
        )

        for bucket_id in SNAPSHOT_BUCKETS:
            snapshot_time = START_TIME + timedelta(
                seconds=bucket_id * BUCKET_SECONDS
            )

            snapshot_id = (
                f"SNAP-{machine_id}-"
                f"{snapshot_time.strftime('%Y%m%d%H%M')}"
            )

            feature_values = grid.loc[bucket_id].to_dict()

            feature_record = {
                "snapshot_id": snapshot_id,
                "machine_id": machine_id,
                "snapshot_timestamp": snapshot_time.isoformat(),
                **feature_values,
            }

            future_limit = snapshot_time + timedelta(
                hours=PREDICTION_HOURS
            )

            target = int(
                any(
                    snapshot_time < failure_time <= future_limit
                    for failure_time in machine_failures
                )
            )

            feature_rows.append(feature_record)

            label_rows.append({
                "snapshot_id": snapshot_id,
                "machine_id": machine_id,
                "snapshot_timestamp": snapshot_time.isoformat(),
                "target_failure_within_24h": target,
            })

    return feature_rows, label_rows


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    connection = connect_database()

    try:
        machine_metadata = load_machine_metadata(connection)

        sensor_data = load_sensor_bucket_aggregates(
            connection
        )

        state_data = load_operating_state_aggregates(
            connection
        )

        failure_events = load_failure_events(connection)

    finally:
        connection.close()

    feature_rows, label_rows = create_snapshot_rows(
        machine_metadata,
        sensor_data,
        state_data,
        failure_events,
    )

    features = pd.DataFrame(feature_rows)
    labels = pd.DataFrame(label_rows)

    features.to_csv(
        FEATURES_PATH,
        index=False,
        na_rep="",
    )

    labels.to_csv(
        LABELS_PATH,
        index=False,
    )

    metadata = {
        "random_seed": 20261022,
        "prediction_horizon_hours": PREDICTION_HOURS,
        "lookback_hours": LOOKBACK_BUCKETS * BUCKET_HOURS,
        "snapshot_interval_hours": BUCKET_HOURS,
        "machines": len(machine_metadata),
        "snapshots": len(features),
        "positive_labels": int(
            labels["target_failure_within_24h"].sum()
        ),
        "negative_labels": int(
            (labels["target_failure_within_24h"] == 0).sum()
        ),
        "feature_count": len([
            column for column in features.columns
            if column not in [
                "snapshot_id",
                "machine_id",
                "snapshot_timestamp",
            ]
        ]),
        "feature_file": str(
            FEATURES_PATH.relative_to(ROOT)
        ),
        "label_file": str(
            LABELS_PATH.relative_to(ROOT)
        ),
        "ground_truth_used_for": (
            "Generating training targets only; "
            "never used as model input features."
        ),
    }

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(metadata, file, indent=4)

    print("\n" + "=" * 55)
    print("ML DATASET GENERATION COMPLETE")
    print("=" * 55)
    print(f"Machines: {metadata['machines']}")
    print(f"Snapshots: {metadata['snapshots']:,}")
    print(f"Features: {metadata['feature_count']}")
    print(f"Positive labels: {metadata['positive_labels']:,}")
    print(f"Negative labels: {metadata['negative_labels']:,}")
    print(f"\nFeatures: {FEATURES_PATH}")
    print(f"Labels: {LABELS_PATH}")
    print(f"Metadata: {METADATA_PATH}")


if __name__ == "__main__":
    main()
