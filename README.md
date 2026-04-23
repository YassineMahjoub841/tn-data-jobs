# tn-data-jobs

An automated pipeline that tracks **data & AI job postings in Tunisia and France**, extracts structured insights from unstructured job descriptions, and publishes a weekly dashboard of what skills and roles are actually in demand.

## What it does

1. **Ingests** job postings weekly from [TanitJobs](https://www.tanitjobs.com) (scraper) and [France Travail](https://francetravail.io) (API).
2. **Transforms** raw postings with dbt — normalising companies, extracting skills, building analytical marts.
3. **Serves** a Streamlit dashboard with top skills, role trends, and company breakdowns.
4. **Runs automatically** every Monday via a GitHub Actions workflow.

## Architecture

<img width="1440" height="1000" alt="Pipeline architecture" src="https://github.com/user-attachments/assets/d267fb40-641f-4f04-b9ed-6eac0a1990cd" />

See [`docs/architecture.md`](docs/architecture.md) for design decisions and a full component breakdown.

## Repository layout

```
tn-data-jobs/
├── README.md
├── docs/
│   ├── architecture.md       # Diagram + design decisions
│   └── weekly-notes.md       # Running changelog
├── ingest/
│   ├── tanitjobs_scraper.py  # BS4 + requests scraper
│   ├── france_travail.py     # France Travail API client
│   └── schemas.py            # Shared Pydantic schemas
├── dbt/
│   ├── models/
│   │   ├── staging/          # stg_tanitjobs, stg_france_travail
│   │   ├── intermediate/     # int_skills_extracted
│   │   └── marts/            # fct_postings, dim_skills, dim_companies
│   └── dbt_project.yml
├── skills_taxonomy/
│   └── skills.yml            # ~200 curated skills + variants
├── dashboard/
│   └── app.py                # Streamlit app
├── .github/workflows/
│   └── weekly_pipeline.yml   # Monday automation
└── pyproject.toml
```

## Quick start

```bash
# Install dependencies (requires uv)
uv sync

# Run scrapers
uv run python -m ingest.tanitjobs_scraper
uv run python -m ingest.france_travail

# Run dbt transformations
cd dbt && dbt run

# Launch dashboard
uv run streamlit run dashboard/app.py
```

## Weekly notes

Progress updates and insight summaries are logged in [`docs/weekly-notes.md`](docs/weekly-notes.md).

## Contributing

PRs and issues are welcome. See [`docs/architecture.md`](docs/architecture.md) for context before contributing.
