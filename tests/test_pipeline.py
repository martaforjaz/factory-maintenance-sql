import csv
import io
from pathlib import Path
import sqlite3
import unittest
from zipfile import ZipFile

from run import build


class PipelineTest(unittest.TestCase):
    def test_reference_outputs(self):
        with sqlite3.connect("file:output/maintenance.sqlite?mode=ro", uri=True) as db:
            self.assertEqual(db.execute("SELECT COUNT(*), SUM(failed) FROM outcomes").fetchone(),
                             (10000, 339))
            self.assertEqual(db.execute("SELECT SUM(violations) FROM quality_checks").fetchone(), (0,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM model_features").fetchone(), (10000,))
            self.assertEqual(db.execute("""
                SELECT failures, observations FROM failure_rates WHERE grade='L' AND wear_band='200+'
            """).fetchone(), (92, 503))
        for name, count in {"quality_checks": 4, "failure_rates": 9, "model_features": 10000}.items():
            with Path(f"output/{name}.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), count)

    def test_invalid_grade_is_rejected(self):
        payload = io.BytesIO()
        with ZipFile(payload, "w") as archive:
            archive.writestr("ai4i2020.csv",
                "UDI,Product ID,Type,Air temperature [K],Process temperature [K],"
                "Rotational speed [rpm],Torque [Nm],Tool wear [min],Machine failure\n"
                "1,X001,X,300,310,1500,20,0,0\n")
        with sqlite3.connect(":memory:") as db:
            with self.assertRaises(sqlite3.IntegrityError):
                build(payload.getvalue(), db)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM telemetry").fetchone(), (0,))
