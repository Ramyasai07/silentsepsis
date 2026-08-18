#!/usr/bin/env python3
"""Read-only validation for the PhysioNet Challenge 2019 training dataset.

This script checks the downloaded PSV files in:
- ai/data/raw/training_setA
- ai/data/raw/training_setB

It validates file counts, empty files, headers, pipe-delimited structure,
SepsisLabel presence, and consistent column layout without modifying the data.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"

EXPECTED_COUNTS = {
    "training_setA": 20_336,
    "training_setB": 20_000,
}
EXPECTED_TOTAL = 40_336


def list_psv_files(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.exists():
        return []
    return sorted(path for path in dataset_dir.glob("*.psv") if path.is_file())


def validate_dataset() -> tuple[bool, list[str], dict[str, int]]:
    issues: list[str] = []
    counts: dict[str, int] = {}
    canonical_header: list[str] | None = None

    for dataset_name in ("training_setA", "training_setB"):
        dataset_dir = RAW_ROOT / dataset_name
        files = list_psv_files(dataset_dir)
        counts[dataset_name] = len(files)

        print(f"{dataset_name}: found {len(files)} .psv files")

        if not dataset_dir.exists():
            issues.append(f"MISSING_DIRECTORY: {dataset_dir}")
            continue

        expected_count = EXPECTED_COUNTS[dataset_name]
        if len(files) != expected_count:
            issues.append(
                f"COUNT_MISMATCH: {dataset_name} expected {expected_count} files, found {len(files)}"
            )

        for path in files:
            rel_path = path.relative_to(REPO_ROOT)

            if path.stat().st_size == 0:
                issues.append(f"EMPTY_FILE: {rel_path}")
                continue

            with path.open("r", encoding="utf-8", newline="") as handle:
                lines = [line.rstrip("\n\r") for line in handle]

            if not lines or not lines[0].strip():
                issues.append(f"MISSING_HEADER: {rel_path}")
                continue

            header = lines[0].strip()
            if "|" not in header:
                issues.append(f"NOT_PIPE_DELIMITED: {rel_path}")
                continue

            header_fields = [field.strip() for field in header.split("|")]
            if not header_fields or any(field == "" for field in header_fields):
                issues.append(f"MALFORMED_HEADER: {rel_path}")
                continue

            if "SepsisLabel" not in header_fields:
                issues.append(f"MISSING_SEPSISLABEL: {rel_path}")
                continue

            if canonical_header is None:
                canonical_header = header_fields
            elif header_fields != canonical_header:
                issues.append(
                    f"INCONSISTENT_HEADER: {rel_path} | "
                    f"expected={canonical_header} | found={header_fields}"
                )

            expected_width = len(header_fields)
            for line_number, line in enumerate(lines[1:], start=2):
                if not line.strip():
                    continue

                row_fields = [field.strip() for field in line.split("|")]
                if len(row_fields) != expected_width:
                    issues.append(
                        f"ROW_WIDTH_MISMATCH: {rel_path} line {line_number} | "
                        f"expected {expected_width} columns, found {len(row_fields)}"
                    )

    total_files = counts.get("training_setA", 0) + counts.get("training_setB", 0)
    if total_files != EXPECTED_TOTAL:
        issues.append(
            f"TOTAL_COUNT_MISMATCH: expected {EXPECTED_TOTAL} files, found {total_files}"
        )

    return (len(issues) == 0), issues, counts


def main() -> None:
    print("PhysioNet Challenge 2019 training dataset validation")
    print(f"Expected counts: training_setA={EXPECTED_COUNTS['training_setA']}, "
          f"training_setB={EXPECTED_COUNTS['training_setB']}, total={EXPECTED_TOTAL}")
    print(f"Data location: {RAW_ROOT}\n")

    passed, issues, counts = validate_dataset()

    print("\nValidation result:")
    if issues:
        print("FAIL")
        print(f"Issues found: {len(issues)}")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("PASS")
        print("No empty files, missing headers, structure issues, or count mismatches detected.")

    print("\nFinal counts:")
    for dataset_name in ("training_setA", "training_setB"):
        print(f"- {dataset_name}: {counts.get(dataset_name, 0)} files")
    print(f"- total: {sum(counts.values())} files")

    if passed:
        print("\nFINAL SUMMARY: PASS")
    else:
        print("\nFINAL SUMMARY: FAIL")


if __name__ == "__main__":
    main()
