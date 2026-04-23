# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions (weekly)               │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │  TanitJobs   │    │ France       │                   │
│  │  Scraper     │    │ Travail API  │                   │
│  │  (BS4+req)   │    │ client       │                   │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                           │
│         └─────────┬─────────┘                           │
│                   ▼                                     │
│         ┌─────────────────┐                             │
│         │  Raw JSON files │                             │
│         │  (data/raw/)    │                             │
│         └────────┬────────┘                             │
│                  │                                      │
│                  ▼                                      │
│         ┌─────────────────┐                             │
│         │   dbt pipeline  │                             │
│         │  staging →      │                             │
│         │  intermediate → │                             │
│         │  marts          │                             │
│         └────────┬────────┘                             │
│                  │                                      │
│                  ▼                                      │
│         ┌─────────────────┐                             │
│         │  DuckDB / files │                             │
│         └────────┬────────┘                             │
│                  │                                      │
│                  ▼                                      │
│         ┌─────────────────┐                             │
│         │  Streamlit app  │                             │
│         └─────────────────┘                             │
└─────────────────────────────────────────────────────────┘
```

## Components

### Ingestion (`ingest/`)

| File | Purpose |
|------|---------|
| `tanitjobs_scraper.py` | Scrapes job listings from tanitjobs.com using `requests` + `BeautifulSoup4`. Paginates through search results and emits raw posting dicts. |
| `france_travail.py` | Calls the France Travail (Pôle Emploi) REST API. Handles OAuth token refresh, pagination and rate-limiting. |
| `schemas.py` | Shared Pydantic models (`RawPosting`, `RawCompany`) that both ingestors produce so downstream code only deals with one shape. |

### Skills taxonomy (`skills_taxonomy/`)

A hand-curated YAML file with ~200 canonical skill names and their common variants/aliases.  dbt's `int_skills_extracted` model uses this list to tag postings.

### Transformation (`dbt/`)

Three-layer medallion architecture:

```
staging         →  intermediate      →  marts
─────────────────────────────────────────────
stg_tanitjobs      int_skills_        fct_postings
stg_france_        extracted          dim_skills
  travail                             dim_companies
```

**Staging** — light-touch cleaning: rename columns, cast types, deduplicate by source URL.

**Intermediate** — cross-source joins and skill extraction against the taxonomy.

**Marts** — denormalised fact and dimension tables ready for the dashboard.

### Dashboard (`dashboard/app.py`)

Streamlit single-page app. Reads from the mart tables (DuckDB by default).  
Key views:
- Top 20 in-demand skills (bar chart)
- Role trend over time (line chart)
- Company breakdown (table)
- Raw postings explorer with full-text search

### Orchestration (`.github/workflows/weekly_pipeline.yml`)

Triggered every Monday at 06:00 UTC.  Steps:

1. Check out repo
2. Install Python deps via `uv`
3. Run `ingest/tanitjobs_scraper.py`
4. Run `ingest/france_travail.py`
5. Run `dbt run` + `dbt test`
6. Commit updated data artefacts back to the repo (or push to a configured store)

## Design decisions

### Why dbt + DuckDB instead of Spark/Airflow?

The data volume is small (hundreds to low-thousands of postings per week).  DuckDB runs in-process without infra.  dbt gives us version-controlled SQL, lineage, and tests for free.

### Why store raw files in the repo?

Keeps the project self-contained with zero cloud costs.  If data grows the raw layer can be moved to S3/GCS with a one-line dbt profile change.

### Why Streamlit?

Fastest path to a shareable dashboard.  Can be deployed to Streamlit Community Cloud for free.

### Why uv?

Faster installs than pip/poetry, single `pyproject.toml`, reproducible lock file without a separate `requirements.txt`.
