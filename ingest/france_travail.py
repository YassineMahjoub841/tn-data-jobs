"""France Travail (Pôle Emploi) API client.

Docs: https://francetravail.io/data/api/offres-emploi
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import requests

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
OUTPUT_DIR = Path("data/raw/france_travail")
DEFAULT_KEYWORDS = ["data engineer", "data analyst", "machine learning", "ingénieur données"]
PAGE_SIZE = 150  # max allowed by the API
REQUEST_DELAY = 0.5  # seconds between requests

logger = logging.getLogger(__name__)


class FranceTravailClient:
    """Thin wrapper around the France Travail offres-emploi REST API."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._session = requests.Session()
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _refresh_token(self) -> None:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload.get("expires_in", 1400) - 60

    def _get_token(self) -> str:
        if self._token is None or time.time() >= self._token_expires_at:
            self._refresh_token()
        return self._token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search_page(self, keyword: str, start: int) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/json",
        }
        params = {
            "motsCles": keyword,
            "range": f"{start}-{start + PAGE_SIZE - 1}",
        }
        resp = self._session.get(SEARCH_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return resp.json()

    def iter_postings(self, keyword: str) -> Iterator[dict[str, Any]]:
        """Yield raw API posting dicts for a keyword, handling pagination."""
        start = 0
        while True:
            data = self._search_page(keyword, start)
            results = data.get("resultats", [])
            if not results:
                break
            yield from results
            content_range = data.get("Content-Range", "")
            # Content-Range: items 0-149/432
            try:
                total = int(content_range.split("/")[1])
            except (IndexError, ValueError):
                break
            start += PAGE_SIZE
            if start >= total:
                break


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a France Travail API result to our common shape."""
    return {
        "source": "france_travail",
        "source_id": raw.get("id", ""),
        "url": raw.get("origineOffre", {}).get("urlOrigine", ""),
        "title": raw.get("intitule", ""),
        "company_name": raw.get("entreprise", {}).get("nom", "Unknown"),
        "location": raw.get("lieuTravail", {}).get("libelle"),
        "contract_type": raw.get("typeContratLibelle"),
        "description": raw.get("description", ""),
        "posted_date": raw.get("dateCreation", "")[:10] or None,
        "scraped_at": date.today().isoformat(),
    }


def run(keywords: list[str] | None = None) -> None:
    """Fetch all keywords and write results to OUTPUT_DIR."""
    client_id = os.environ["FRANCE_TRAVAIL_CLIENT_ID"]
    client_secret = os.environ["FRANCE_TRAVAIL_CLIENT_SECRET"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    keywords = keywords or DEFAULT_KEYWORDS
    today = date.today().isoformat()
    client = FranceTravailClient(client_id, client_secret)

    results: list[dict] = []
    seen: set[str] = set()

    for keyword in keywords:
        logger.info("Fetching keyword: %s", keyword)
        for raw in client.iter_postings(keyword):
            normalised = _normalise(raw)
            uid = normalised["source_id"]
            if uid and uid not in seen:
                seen.add(uid)
                results.append(normalised)

    out_path = OUTPUT_DIR / f"{today}.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote %d postings to %s", len(results), out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
