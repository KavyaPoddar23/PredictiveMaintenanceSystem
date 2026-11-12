
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "validation_reports"

BASELINE = REPORT_DIR / "checksums_baseline.json"
CURRENT = REPORT_DIR / "checksums.json"


def load_checksums(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    if not BASELINE.exists():
        raise FileNotFoundError(
            "Baseline checksum file not found. "
            "Save checksums.json as checksums_baseline.json first."
        )

    if not CURRENT.exists():
        raise FileNotFoundError(
            "Current checksums.json not found. "
            "Run Phase 6 validation first."
        )

    baseline = load_checksums(BASELINE)
    current = load_checksums(CURRENT)

    baseline_files = set(baseline)
    current_files = set(current)

    added = current_files - baseline_files
    removed = baseline_files - current_files

    changed = {
        path
        for path in baseline_files & current_files
        if baseline[path] != current[path]
    }

    print("\nREPRODUCIBILITY REPORT")
    print("=" * 45)

    print(f"Baseline files: {len(baseline_files)}")
    print(f"Current files:  {len(current_files)}")
    print(f"Added files:    {len(added)}")
    print(f"Removed files:  {len(removed)}")
    print(f"Changed files:  {len(changed)}")

    if added:
        print("\nAdded:")
        for path in sorted(added):
            print(path)

    if removed:
        print("\nRemoved:")
        for path in sorted(removed):
            print(path)

    if changed:
        print("\nChanged:")
        for path in sorted(changed):
            print(path)

    if not added and not removed and not changed:
        print("\nPASS: Dataset is reproducible.")
    else:
        print("\nFAIL: Dataset outputs differ.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
