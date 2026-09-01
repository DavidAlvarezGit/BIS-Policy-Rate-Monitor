# BIS Policy Rate Monitor

A data pipeline that discovers and downloads the latest
Bank for International Settlements (BIS) central bank policy-rate dataset,
transforms it into a tidy dataset, and produces country-level
summaries, a chart, and a Markdown report.

The project implements a command-line interface and uses the BIS SDMX API to
validate country and area codes and provide “did you mean” suggestions.

## Pipeline overview

```text
BIS bulk-download page              BIS SDMX API
          |                              |
          v                              v
WS_CBPOL_csv_flat.zip                 reference-area codelist
          |                              |
          +--------------+---------------+
                         |
                         v
              validated tidy dataset
                         |
                         v
               country-level summary
                         |
            +------------+------------+
            |            |            |
            v            v            v
      CSV and JSON      chart     Markdown report
```

The pipeline has three explicit stages:

1. **Fetch** discovers the current `WS_CBPOL` CSV-flat download instead of
   relying on a hard-coded file URL. It caches the ZIP and the BIS
   reference-area codelist under `data/raw/`.
2. **Transform** validates the source schema, normalizes BIS labels and dates,
   preserves descriptive series attributes, removes exact duplicates, and
   rejects conflicting observations.
3. **Report** selects requested countries, prefers daily observations with a
   monthly fallback and computes the latest snapshot.

## Repository layout

```text
src/bis_prates/
  cli.py          Command-line interface
  ingestion.py    Bulk-download discovery and SDMX metadata retrieval
  metadata.py     Country-code validation and aliases
  transform.py    Source validation and tidy-data transformation
  summary.py      Snapshot and policy-rate change calculations
  report.py       Chart and Markdown report generation
tests/             Unit tests for ingestion, transformation, summaries, and reports
.github/workflows/
  ci.yaml          GitHub Actions checks for linting, formatting, and tests
notebooks/         Exploratory analysis
data/raw/          Cached source files; ignored by Git
data/processed/    Generated tidy dataset; ignored by Git
out/               Summary files, chart, and report
```

## Requirements

- Python 3.12 or later
- [`uv`](https://docs.astral.sh/uv/) for dependency and environment management

## Installation

Clone the repository and create the locked environment:

```bash
git clone <repository-url>
cd BIS-Policy-Rate-Monitor
uv sync --locked --all-extras --dev
```

The CLI can then be run through `uv`.

```bash
uv run bis-prates --help
```

## Running the pipeline

Run the stages in order from the repository root.

### 1. Fetch and cache the BIS sources

```bash
uv run bis-prates fetch
```

### 2. Transform the source dataset

```bash
uv run bis-prates transform
```

This produces `data/processed/policy_rates.csv`.

### 3. Generate a report

```bash
uv run bis-prates report \
  --countries "ES,US,EA,GB,JP,CH" \
  --start "2015-01-01"
```

Invalid codes produce a suggestion when a sufficiently
close match exists.

The report command creates:

| Output | Description |
| --- | --- |
| `out/summary.csv` | Latest snapshot for analysis |
| `out/summary.json` | Structured snapshot with metadata |
| `out/policy_rates.png` | Policy-rate history by country or area |
| `out/report.md` | Report with a table, chart, and methodology |

## Data contract and methodology

Each observation is uniquely identified by:

```text
country_code + frequency + observation_date
```

The pipeline applies the following rules:

- Daily observations are preferred within each country-month; monthly observations are used as a fallback and they are normalized to calendar month-end dates.
- Countries without observations in the reporting period are excluded from the snapshot and reported separately with their latest historical observation and relevant BIS metadata.
- Country and area codes are validated against the BIS codelist, with fuzzy matching used to suggest a close code when validation fails.
- The task uses `EA` for the euro area, while BIS uses `XM`; the CLI resolves `EA` to `XM` and records both requested and BIS codes in the JSON output.

Source data is cached locally for repeated runs; use `fetch --refresh` to refresh download. The `data/` directory is excluded from
version control.

## Tests and continuous integration

Run the same checks/tests locally that are used in CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

The GitHub Actions workflow in `.github/workflows/ci.yaml` runs these checks on
every push and pull request to `main`. It installs Python and the locked project
environment with `uv sync --locked --all-extras --dev`, so CI uses the same
dependency versions recorded in `uv.lock`.

## AI usage note

I used OpenAI Codex (GPT-5.6) to help draft and review code, tests, and
documentation. I treated its suggestions as a starting point and simplified or
rejected them when they did not fit the task. The most common issue was
unnecessary complexity: at one stage, the report code grew beyond 700 lines for a
fairly small reporting requirement. Codex also sometimes changed one module
without updating another. For example, changing the values returned by
`report.py` left `cli.py` trying to unpack the old result. In another case, a
request to remove one historical chart was interpreted as removing all plots.
Reviewing the full diff and running the CI checks helped catch these problems.

The data itself also needed manual interpretation. Spain's national policy-rate
series ends before the selected reporting period because monetary policy moved
to the euro-area level; it is not simply missing because of a pipeline error. I
checked the BIS metadata and historical observations to distinguish discontinued
series from processing problems. This was a useful reminder that AI can speed up
implementation, but it does not replace end-to-end review.

## Data source

Bank for International Settlements, **Central bank policy rates** (`WS_CBPOL`),
retrieved from the BIS Data Portal bulk-download service. Country and area
metadata is retrieved from the BIS SDMX API codelist `CL_BIS_GL_REF_AREA`.
