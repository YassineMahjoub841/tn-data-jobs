# tn-data-jobs

**An automated pipeline that tracks data and AI job postings in Tunisia and France, extracts structured insights from unstructured job descriptions, and publishes a weekly dashboard of what skills and roles are actually in demand.**

🔗 **Live dashboard:** _coming week 5-6_
📝 **Weekly notes:** [`docs/weekly-notes.md`](docs/weekly-notes.md)

---

## Why this exists

I'm a recent Tunisian engineering grad trying to understand what the data/AI job market in Tunisia and France actually looks like — not what LinkedIn thinks I should learn, but what companies are hiring for right now. Job boards give you one posting at a time. I wanted the aggregate view.

So I'm building a pipeline that scrapes and ingests postings weekly, extracts skills and roles from the text, and makes the results public. Other job-seekers can see what's in demand. I get a portfolio project. Everyone wins.

## Architecture

![Architecture diagram](docs/architecture.png)

The short version:

- **Ingest** — Python scraper for Tanitjobs (Tunisia) + API client for France Travail (France, public API). Normalized JSON lands in Google Cloud Storage.
- **Warehouse** — Raw postings land in BigQuery as an append-only table. Historical snapshots preserved.
- **Transform** — dbt models clean, deduplicate, and extract structured skills from job description text using a curated taxonomy.
- **Serve** — Streamlit dashboard for browsing, weekly LinkedIn post with the most interesting finding of the week.
- **Orchestrate** — GitHub Actions on weekly cron (v1), migrating to Kestra in v2.

## Repo layout

```
.
├── ingest/               # Scrapers and API clients
├── dbt/                  # Warehouse transformations
├── skills_taxonomy/      # Curated skill list + variants
├── dashboard/            # Streamlit app
├── notebooks/            # Exploratory analysis
├── docs/                 # Architecture notes, weekly changelog
└── .github/workflows/    # Scheduled pipeline runs
```

## Roadmap

- [x] Project scoping + architecture
- [ ] **Weeks 1–2:** Walking skeleton — scrapers landing raw data in BigQuery, first exploratory notebook
- [ ] **Weeks 3–4:** dbt transformations + skill extraction, first insight post
- [ ] **Weeks 5–6:** Streamlit dashboard, public deployment, weekly automation
- [ ] **Weeks 7–8:** Migration to Kestra orchestration OR semantic clustering of JDs

## Running locally

_To be filled in as the project stabilizes. For now, see individual module READMEs._

## Design notes

Decisions I've made and why, in [`docs/architecture.md`](docs/architecture.md). Things I've learned the hard way, in [`docs/weekly-notes.md`](docs/weekly-notes.md).

## License

MIT. If you use this data or code, a link back is appreciated.

---

*Built by [Yassine Mahjoub](https://www.linkedin.com/in/yassine-mahjoub/). Open to feedback, issues, and PRs.*
