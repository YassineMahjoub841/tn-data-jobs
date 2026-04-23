"""
Load normalized postings into BigQuery `raw.jobs`.

Design: append-only. We never update or delete rows here. Deduplication and
deletion happen in dbt's staging layer. This keeps 'raw' actually raw — if we
discover a bug in parsing later, we can re-run staging without re-scraping.

Schema (create manually once, or via Terraform in v2):

  CREATE TABLE `<project>.raw.jobs` (
    source            STRING    NOT NULL,
    source_job_id     STRING    NOT NULL,
    source_url        STRING    NOT NULL,
    scraped_at        TIMESTAMP NOT NULL,
    title             STRING    NOT NULL,
    company           STRING,
    location          STRING,
    country           STRING,
    description       STRING    NOT NULL,
    posted_at         TIMESTAMP,
    contract_type     STRING,
    experience_level  STRING,
    remote            STRING,
    raw_payload       STRING    -- JSON-encoded
  )
  PARTITION BY DATE(scraped_at)
  CLUSTER BY source;

`raw_payload` is STRING rather than JSON to keep the loader simple and
schemaless. Upgrade to the JSON type later if you need to query into it.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from google.cloud import bigquery

from .schemas import RawJobPosting

logger = logging.getLogger(__name__)


def load_postings(
    postings: Iterable[RawJobPosting],
    *,
    project: str | None = None,
    dataset: str = "raw",
    table: str = "jobs",
    batch_size: int = 500,
) -> int:
    """
    Stream-insert postings into `<project>.<dataset>.<table>`.

    Returns the number of rows inserted.
    """
    project = project or os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project)
    table_ref = client.dataset(dataset).table(table)

    batch: list[dict] = []
    total = 0

    def flush():
        nonlocal batch, total
        if not batch:
            return
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            # Don't silently swallow — we want to notice this
            raise RuntimeError(f"BigQuery insert errors: {errors}")
        total += len(batch)
        logger.info(f"Inserted {len(batch)} rows (total this run: {total})")
        batch = []

    for posting in postings:
        batch.append(posting.to_bq_row())
        if len(batch) >= batch_size:
            flush()
    flush()

    return total
