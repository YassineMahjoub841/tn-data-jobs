"""TanitJobs scraper — collects data & AI job postings from tanitjobs.com."""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Iterator
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ingest.schemas import RawPosting

BASE_URL = "https://www.tanitjobs.com"
SEARCH_PATH = "/jobs/"
DEFAULT_KEYWORDS = ["data", "data engineer", "data analyst", "machine learning", "AI"]
OUTPUT_DIR = Path("data/raw/tanitjobs")
REQUEST_DELAY = 1.5  # seconds between requests

logger = logging.getLogger(__name__)


def _get(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY)
    return BeautifulSoup(response.text, "html.parser")


def _parse_listing_page(soup: BeautifulSoup) -> list[dict]:
    """Extract job cards from a search-results page."""
    postings = []
    for card in soup.select("div.job-listing"):
        title_tag = card.select_one("h2.job-title a")
        company_tag = card.select_one("span.company-name")
        location_tag = card.select_one("span.job-location")
        date_tag = card.select_one("span.job-date")
        if not title_tag:
            continue
        postings.append(
            {
                "title": title_tag.get_text(strip=True),
                "url": urljoin(BASE_URL, title_tag["href"]),
                "company_name": company_tag.get_text(strip=True) if company_tag else "",
                "location": location_tag.get_text(strip=True) if location_tag else None,
                "posted_date_raw": date_tag.get_text(strip=True) if date_tag else None,
            }
        )
    return postings


def _parse_detail_page(soup: BeautifulSoup) -> str:
    """Extract the full description from a job detail page."""
    desc_tag = soup.select_one("div.job-description")
    return desc_tag.get_text(separator="\n", strip=True) if desc_tag else ""


def _next_page_url(soup: BeautifulSoup) -> str | None:
    """Return the URL of the next search-results page, or None."""
    next_link = soup.select_one("a.next-page")
    if next_link and next_link.get("href"):
        return urljoin(BASE_URL, next_link["href"])
    return None


def scrape(keyword: str, max_pages: int = 20) -> Iterator[RawPosting]:
    """Yield RawPosting objects for a given search keyword."""
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; tn-data-jobs-bot/1.0; "
        "+https://github.com/YassineMahjoub841/tn-data-jobs)"
    )

    url: str | None = f"{BASE_URL}{SEARCH_PATH}?q={keyword.replace(' ', '+')}"
    page = 0

    while url and page < max_pages:
        logger.info("Fetching listing page %d: %s", page + 1, url)
        soup = _get(session, url)
        cards = _parse_listing_page(soup)

        for card in cards:
            try:
                detail_soup = _get(session, card["url"])
                description = _parse_detail_page(detail_soup)
                yield RawPosting(
                    source="tanitjobs",
                    source_id=card["url"].split("/")[-2] or card["url"],
                    url=card["url"],
                    title=card["title"],
                    company_name=card["company_name"] or "Unknown",
                    location=card.get("location"),
                    description=description,
                    scraped_at=date.today(),
                )
            except Exception:
                logger.exception("Failed to scrape detail page: %s", card.get("url"))

        url = _next_page_url(soup)
        page += 1


def run(keywords: list[str] | None = None, max_pages: int = 20) -> None:
    """Scrape all keywords and write results to OUTPUT_DIR."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    keywords = keywords or DEFAULT_KEYWORDS
    today = date.today().isoformat()
    results = []

    for keyword in keywords:
        logger.info("Scraping keyword: %s", keyword)
        for posting in scrape(keyword, max_pages=max_pages):
            results.append(posting.model_dump(mode="json"))

    # Deduplicate by URL
    seen: set[str] = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    out_path = OUTPUT_DIR / f"{today}.json"
    out_path.write_text(json.dumps(unique, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote %d postings to %s", len(unique), out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
