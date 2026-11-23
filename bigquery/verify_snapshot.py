"""Run the GoogleSQL snapshot against BigQuery, then compare SQLite cohorts."""
import argparse
import csv
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from google.cloud import bigquery

from parity import compare, indexed

ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    ("observation_id", "INTEGER"), ("product_id", "STRING"), ("grade", "STRING"),
    ("air_k", "FLOAT"), ("process_k", "FLOAT"), ("rpm", "INTEGER"),
    ("torque_nm", "FLOAT"), ("wear_min", "INTEGER"), ("failed", "INTEGER"),
    *((field, "INTEGER") for field in ("twf", "hdf", "pwf", "osf", "rnf")),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--zip", required=True, type=Path)
    args = parser.parse_args()
    client = bigquery.Client(project=args.project, location="US")
    table = f"{args.project}.{args.dataset}.ai4i_demo_{uuid4().hex[:10]}"
    schema = [bigquery.SchemaField(name, kind) for name, kind in FIELDS]
    config = bigquery.LoadJobConfig(schema=schema, skip_leading_rows=1,
                                    source_format=bigquery.SourceFormat.CSV,
                                    write_disposition=bigquery.WriteDisposition.WRITE_EMPTY)
    with ZipFile(args.zip) as archive:
        source = archive.read("ai4i2020.csv")
    client.create_table(bigquery.Table(table, schema=schema))
    try:
        client.load_table_from_file(BytesIO(source), table, job_config=config).result()
        sql = (ROOT / "bigquery/analytics.sql").read_text(encoding="utf-8")
        sql = sql.replace("factory_maintenance.ai4i_raw", table)
        for name in ("model_features", "failure_rates"):
            sql = sql.replace(f"CREATE OR REPLACE TABLE `factory_maintenance.{name}`",
                              f"CREATE TEMP TABLE {name}")
        sql += "\nSELECT * FROM failure_rates;\n"
        job = client.query(sql, job_config=bigquery.QueryJobConfig(
            use_query_cache=False, maximum_bytes_billed=200_000_000))
        cloud = indexed([dict(row) for row in job.result()])
        with (ROOT / "output/failure_rates.csv").open(encoding="utf-8", newline="") as file:
            local = indexed(list(csv.DictReader(file)))
        compare(local, cloud)
        children = sorted(client.list_jobs(parent_job=job.job_id), key=lambda child: child.created)
        evidence = {
            "job_id": job.job_id, "cohorts_matching_sqlite": len(cloud),
            "processed_bytes": job.total_bytes_processed,
            "billed_bytes": job.total_bytes_billed,
            "children": [{"statement": child.statement_type, "processed_bytes": child.total_bytes_processed}
                         for child in children],
        }
        print(json.dumps(evidence, indent=2))
    finally:
        client.delete_table(table, not_found_ok=True)


if __name__ == "__main__":
    main()
