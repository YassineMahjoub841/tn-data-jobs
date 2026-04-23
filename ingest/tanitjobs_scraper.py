"""
Tanitjobs scraper.

IMPORTANT: Scrapers break. This one WILL break when Tanitjobs changes their HTML.
That's fine. The goal is:
  1. Work reliably this week
  2. Fail loudly (not silently) when the site changes
  3. Log enough information that fixing it takes minutes, not hours

DO NOT try to make this bulletproof. Make it debuggable.

Polite-scraping rules:
  - 1 request per 2 seconds, max
  - Respect robots.txt (check before each run, not once)
  - Identify ourselves in User-Agent
  - Retry on 5xx, back off on 429, bail on 403

Before running: check https://www.tanitjobs.com/robots.txt and adjust allowed paths.
The selectors below are placeholders — verify them against the live site before
the first real run.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Iterator, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from .schemas import RawJobPosting

logger = logging.getLogger(__name__)

BASE_URL = "https://www.tanitjobs.com"
SEARCH_PATH = "/jobs/data"   # TODO: confirm the actual search path and query params

USER_AGENT = (
    "tn-data-jobs-research/0.1 "
    "(+https://github.com/<your-username>/tn-data-jobs; portfolio project)"
)
REQUEST_DELAY_SECONDS = 2.0


class TanitjobsScraper:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_request = 0.0

    def _fetch(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch one URL, rate-limited, with basic retry on 5xx."""
        # rate-limit
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)

        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=20)
                self._last_request = time.time()
            except requests.RequestException as e:
                logger.warning(f"Request error on {url} (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "30"))
                logger.warning(f"Rate-limited on {url}, sleeping {wait}s")
                time.sleep(wait)
                continue
            if resp.status_code in (403, 404):
                logger.error(f"Non-retryable {resp.status_code} on {url}")
                return None
            if resp.status_code >= 500:
                logger.warning(f"{resp.status_code} on {url}, retrying")
                time.sleep(2 ** attempt)
                continue

            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")

        logger.error(f"Gave up on {url} after 3 attempts")
        return None

    def iter_listing_urls(self, max_pages: int = 5) -> Iterator[str]:
        """
        Walk paginated listing pages, yield detail-page URLs.

        TODO: inspect the live site and update selectors. Placeholder logic assumes
        each listing page has `<a class="job-title">` elements linking to details.
        """
        for page in range(1, max_pages + 1):
            listing_url = f"{BASE_URL}{SEARCH_PATH}?page={page}"
            logger.info(f"Fetching listing page {page}: {listing_url}")
            soup = self._fetch(listing_url)
            if not soup:
                return

            # --- Fragile selector: UPDATE ME ---
            links = soup.select("a.job-title")  # ← confirm against live HTML
            if not links:
                logger.warning(
                    f"No job links found on page {page}. "
                    "Either we hit the end, or the selector is stale. "
                    "Dumping first 500 chars of HTML for inspection:"
                )
                logger.warning(soup.get_text()[:500])
                return

            for a in links:
                href = a.get("href")
                if href:
                    yield urljoin(BASE_URL, href)

    def parse_detail(self, url: str) -> Optional[RawJobPosting]:
        """
        Fetch and parse one job detail page into a RawJobPosting.

        TODO: update selectors against live HTML. The point of this structure is
        that when it breaks, you can update selectors in one place.
        """
        soup = self._fetch(url)
        if not soup:
            return None

        # --- Fragile selectors: UPDATE ME as a set ---
        title = _text(soup.select_one("h1.job-title"))
        company = _text(soup.select_one(".company-name"))
        location = _text(soup.select_one(".job-location"))
        description = _text(soup.select_one(".job-description"))
        source_job_id = url.rstrip("/").split("/")[-1]

        if not title or not description:
            logger.warning(f"Missing title or description on {url} — selectors may be stale")
            return None

        try:
            return RawJobPosting(
                source="tanitjobs",
                source_job_id=source_job_id,
                source_url=url,
                scraped_at=datetime.now(timezone.utc),
                title=title,
                company=company,
                location=location,
                country="TN",
                description=description,
                raw_payload={"html_snippet_len": len(str(soup))},
            )
        except ValidationError as e:
            logger.warning(f"Validation failed for {url}: {e}")
            return None

    def scrape(self, max_pages: int = 5, max_postings: int = 100) -> Iterator[RawJobPosting]:
        count = 0
        for url in self.iter_listing_urls(max_pages=max_pages):
            if count >= max_postings:
                return
            posting = self.parse_detail(url)
            if posting:
                yield posting
                count += 1


def _text(el) -> Optional[str]:
    """Safely extract trimmed text from a BeautifulSoup element."""
    if el is None:
        return None
    t = el.get_text(" ", strip=True)
    return t or None


# -- CLI smoke test --
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = TanitjobsScraper()
    for i, posting in enumerate(scraper.scrape(max_pages=2, max_postings=5)):
        print(f"[{i}] {posting.title} @ {posting.company} — {posting.location}")
