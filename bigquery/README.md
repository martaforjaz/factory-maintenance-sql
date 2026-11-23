# BigQuery implementation

This GoogleSQL port recreates the feature and cohort outputs from the same UCI snapshot. It uses a typed landing table, SQL assertions, and two output tables.

From the repository root, download and unpack the UCI archive linked in the main README. Use a Google Cloud project with BigQuery enabled and the authenticated `bq` CLI. The following Bash commands use the active project. Create a dedicated dataset for this example because the script replaces its two output tables.

```bash
bq --location=US mk --dataset factory_maintenance
bq --location=US load --source_format=CSV --skip_leading_rows=1 \
  factory_maintenance.ai4i_raw ai4i2020.csv \
  'observation_id:INTEGER,product_id:STRING,grade:STRING,air_k:FLOAT,process_k:FLOAT,rpm:INTEGER,torque_nm:FLOAT,wear_min:INTEGER,failed:INTEGER,twf:INTEGER,hdf:INTEGER,pwf:INTEGER,osf:INTEGER,rnf:INTEGER'
bq --location=US query --use_legacy_sql=false < bigquery/analytics.sql
```

To verify parity with SQLite, run the local pipeline and export all nine cloud cohorts:

```bash
python run.py
bq --location=US query --use_legacy_sql=false --format=prettyjson --max_rows=100 \
  'SELECT * FROM `factory_maintenance.failure_rates`' > output/bq-cohorts.json
python bigquery/parity.py output/bq-cohorts.json
```

The comparison checks cohort keys, counts, ranks, and rates. The reference snapshot has 10,000 observations and 339 failures. A configured Google Cloud project is required to execute this BigQuery version.
