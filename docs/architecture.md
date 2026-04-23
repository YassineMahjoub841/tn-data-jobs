# Architecture & design decisions

This is the "why" companion to the README's "what". When something looks weird in the code, this file should explain the tradeoff I considered.

## Data sources

**Tanitjobs (Tunisia)** — Scraped. The site doesn't have an API, but HTML is relatively stable. Accept that scrapers break; log failures loudly and fix on a weekly cadence rather than trying to build a bulletproof scraper.

**France Travail API (France)** — Public API, requires free registration at https://francetravail.io/. Chosen over LinkedIn and Indeed scraping because (a) it's a legitimate public API, (b) ToS-compliant, (c) returns structured JSON, no parsing needed. Tradeoff: France Travail skews toward non-tech and publicly-listed positions, so it may underrepresent startups and tech-consultancy jobs. Plan to add a second French source in v2 if needed.

## Warehouse: BigQuery

Chosen over Postgres because:
- Free tier is generous (1 TB of query per month free; this project will use megabytes).
- It's what most modern data teams use. Credible signal on a CV.
- It's the Zoomcamp's warehouse, so project time doubles as course practice.
- Column-store + SQL dialect forces habits that transfer to Snowflake, Redshift, Databricks.

Tradeoff: latency on tiny queries is higher than Postgres. For this scale (thousands of rows), it doesn't matter.

## Transformations: dbt

The alternative was raw SQL scripts or Python transforms. dbt wins because:
- Version-controlled SQL with tests is standard in modern analytics engineering.
- Forces a layered structure (staging → intermediate → marts) that's genuinely clearer.
- Tests catch schema drift from the scrapers.
- Good portfolio signal.

Tradeoff: adds a tool to learn. Acceptable because it's industry-standard.

## Skill extraction: keyword matching first

I could use embeddings + clustering from day one. I'm not, because:
- A curated taxonomy is transparent, auditable, and correctable. Embeddings are a black box until you evaluate them properly.
- 80% of the value lives in ~200 well-chosen keywords.
- It's trivially explainable in an interview.

v2 will layer semantic methods on top to find *themes* that aren't in the taxonomy (e.g. "stakeholder management", "product thinking"). The keyword layer stays as ground truth.

## Orchestration: GitHub Actions → Kestra

v1 uses GitHub Actions on cron. It's free, one YAML file, ships week 5-6.

v2 migrates to Kestra. The migration is deliberate — "I started simple and re-architected when I needed real retry logic, observability, and multi-step dependencies" is a better interview story than picking the heaviest tool on day one.

## Dashboard: Streamlit

Chosen over Power BI, Metabase, and Superset because:
- Pure Python — no additional tool to maintain.
- Streamlit Community Cloud is free and public.
- Easy to iterate on in PRs.

I'll probably build a Power BI version in parallel once the data stabilizes, because BI-literacy is an asset on the Data Analyst CV.

## What's explicitly NOT in scope (for v1)

- User accounts, saved searches, job alerts.
- Historical deduplication across sources (same job listed on both Tanitjobs and France Travail — unlikely at this scale anyway).
- Real-time anything. Weekly cadence is the point.
- ML-based role classification. The role field from sources is good enough for v1.
- Salary data. Most postings don't include it reliably.

## Open questions / things I'll probably get wrong

- How often does Tanitjobs change its HTML structure? Week 2 me will have a better answer than week 1 me.
- Is skill keyword matching precise enough for French-language postings? Probably needs per-language variants.
- Should raw data be deduplicated at ingest or at the staging layer? Leaning toward staging — keep raw raw.
