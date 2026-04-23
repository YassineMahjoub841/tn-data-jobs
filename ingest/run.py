"""
End-to-end run: scrape + API fetch → normalize → load to BigQuery.

Usage:
  python -m ingest.run --source all --max 100
  python -m ingest.run --source france_travail --max 500
  python -m ingest.run --source tanitjobs --dry-run    # doesn't write to BQ
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .bigquery_loader import load_postings
from .france_travail import FranceTravailClient
from .schemas import RawJobPosting
from .tanitjobs_scraper import TanitjobsScraper

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def from_france_travail(max_per_query: int = 200):
    client = FranceTravailClient()
    # A starting set of queries. Tune these as you learn the data.
    queries = ["data engineer", "data analyst", "machine learning", "data scientist"]
    for query in queries:
        logger.info(f"France Travail: query='{query}'")
        for raw in client.search(query, max_results=max_per_query):
            posting = client.to_raw_posting(raw)
            if posting:
                yield posting


def from_tanitjobs(max_postings: int = 100):
    scraper = TanitjobsScraper()
    yield from scraper.scrape(max_pages=10, max_postings=max_postings)


def dump_to_jsonl(postings, path: Path) -> int:
    """Write postings to a local JSONL file as a backup / for dry-runs."""
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for p in postings:
            f.write(json.dumps(p.to_bq_row(), ensure_ascii=False))
            f.write("\n")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["all", "tanitjobs", "france_travail"], default="all")
    parser.add_argument("--max", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true",
                        help="Write to JSONL instead of BigQuery")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    if args.source == "all":
        postings = list(from_france_travail(max_per_query=args.max)) + list(from_tanitjobs(max_postings=args.max))
    elif args.source == "france_travail":
        postings = list(from_france_travail(max_per_query=args.max))
    else:
        postings = list(from_tanitjobs(max_postings=args.max))

    logger.info(f"Collected {len(postings)} postings")

    if args.dry_run:
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        out = DATA_DIR / f"postings-{stamp}.jsonl"
        n = dump_to_jsonl(iter(postings), out)
        logger.info(f"Wrote {n} postings to {out}")
    else:
        n = load_postings(iter(postings))
        logger.info(f"Loaded {n} postings to BigQuery")


if __name__ == "__main__":
    main()
