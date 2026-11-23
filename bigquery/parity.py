"""Compare BigQuery's cohort JSON export with the local SQLite CSV."""
import csv
import json
from math import isclose
from pathlib import Path
import sys


def indexed(rows):
    result = {(row["grade"], row["wear_band"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate cohort keys")
    return result


def compare(local, cloud):
    if local.keys() != cloud.keys():
        raise ValueError("Cohort keys differ")
    for key, left in local.items():
        right = cloud[key]
        for field in ("observations", "failures", "risk_rank_within_grade"):
            if int(left[field]) != int(right[field]):
                raise ValueError(f"{key}: {field} differs")
        for field in ("failure_rate", "failure_pct"):
            if not isclose(float(left[field]), float(right[field]), rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError(f"{key}: {field} differs")


if __name__ == "__main__":
    with Path("output/failure_rates.csv").open(newline="", encoding="utf-8") as stream:
        expected = indexed(list(csv.DictReader(stream)))
    actual = indexed(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig")))
    compare(expected, actual)
    print(f"SQLite and BigQuery agree on {len(expected)} cohorts.")
