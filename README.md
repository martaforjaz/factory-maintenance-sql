# Factory Maintenance SQL Pipeline

How does the observed failure rate vary across product grades and tool wear bands? This project turns a public manufacturing benchmark into a validated SQLite database, a cohort report, and a feature extract suitable for downstream ML experiments.

## Run locally

Requires Python 3.11+ with SQLite 3.37+. No Python packages or cloud account needed.

```sh
python run.py
```

Use `--zip path/to/dataset.zip` for an offline run. The command creates `output/maintenance.sqlite` and exports three CSV files. Each run rebuilds from the input rather than appending rows.

| Output | Purpose |
| --- | --- |
| `quality_checks.csv` | Source row count, outcome coverage, grade consistency, and temperature ordering |
| `failure_rates.csv` | Cohort size, labeled failures, observed failure rate, and within-grade ranking |
| `model_features.csv` | Sensor measurements and engineered features. Use observation ID only as a join key. |

The Python loader parses the CSV into typed telemetry and outcome tables linked by an observation key. SQL enforces uniqueness, value checks, and referential integrity. SQL views also calculate temperature difference and rotational power from RPM and torque. Failure labels and failure-mode flags are excluded from the feature columns.

## Findings

The source contains 10,000 observations and 339 labeled failures (3.39%). The 200+ minute tool-wear band has the highest observed failure rate in each grade. For grade L, that is 92 failures in 503 observations (18.29%), compared with 69 in 2,754 observations (2.51%) in the 0–99 minute band.

These are descriptive rates for a synthetic benchmark. Tool wear contributes to the dataset's failure-generation rules, so the association does not establish a real-world maintenance threshold. The project produces features and analytics for experimentation and does not train a model.

## Data source

Stephan Matzka, *AI4I 2020 Predictive Maintenance Dataset*, UCI Machine Learning Repository (2020). [Dataset and citation](https://doi.org/10.24432/C5HS5C) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source archive is fetched directly from UCI. The input CSV SHA-256 used for the findings is `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`.
