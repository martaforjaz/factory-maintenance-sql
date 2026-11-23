"""Build and validate a local SQLite analytics database from the UCI snapshot."""
import argparse
import csv
import hashlib
import io
from pathlib import Path
import sqlite3
from urllib.request import urlopen
from zipfile import ZipFile

SOURCE = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"
ROOT = Path(__file__).resolve().parent


def build(payload, db, *, resume=False):
    with ZipFile(io.BytesIO(payload)) as archive:
        raw = archive.read("ai4i2020.csv")
    db.execute("PRAGMA foreign_keys = ON")
    if not resume:
        db.executescript((ROOT / "analytics.sql").read_text(encoding="utf-8"))
    with db:
        for record in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
            key = int(record["UDI"])
            telemetry = (
                key, record["Product ID"], record["Type"],
                float(record["Air temperature [K]"]), float(record["Process temperature [K]"]),
                int(record["Rotational speed [rpm]"]), float(record["Torque [Nm]"]),
                int(record["Tool wear [min]"]),
            )
            outcome = (key, int(record["Machine failure"]))
            if resume:
                existing = db.execute("SELECT * FROM telemetry WHERE observation_id = ?", (key,)).fetchone()
                if existing is not None:
                    existing_outcome = db.execute(
                        "SELECT * FROM outcomes WHERE observation_id = ?", (key,)
                    ).fetchone()
                    if existing != telemetry or existing_outcome != outcome:
                        raise ValueError(f"Conflicting replay for observation {key}")
                    continue
            db.execute("INSERT INTO telemetry VALUES (?, ?, ?, ?, ?, ?, ?, ?)", telemetry)
            db.execute("INSERT INTO outcomes VALUES (?, ?)", outcome)
        failures = db.execute("SELECT * FROM quality_checks WHERE violations <> 0").fetchall()
        if failures:
            raise ValueError(f"Data quality checks failed: {failures}")
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Use a previously downloaded UCI ZIP")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    if args.zip:
        payload = args.zip.read_bytes()
    else:
        with urlopen(SOURCE, timeout=30) as response:
            payload = response.read()
    with sqlite3.connect(":memory:") as db:
        checksum = build(payload, db)
        args.output.mkdir(parents=True, exist_ok=True)
        for name, order in (
            ("quality_checks", "check_name"),
            ("failure_rates", "grade, risk_rank_within_grade, wear_band"),
            ("model_features", "observation_id"),
        ):
            results = db.execute(f"SELECT * FROM {name} ORDER BY {order}")
            with (args.output / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(column[0] for column in results.description)
                writer.writerows(results)
        with sqlite3.connect(args.output / "maintenance.sqlite") as target:
            db.backup(target)
        print("CSV SHA-256:", checksum)
        print("Observations and failures:", db.execute("SELECT COUNT(*), SUM(failed) FROM outcomes").fetchone())


if __name__ == "__main__":
    main()
