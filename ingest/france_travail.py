"""
France Travail ("Offres d'emploi v2") API client.

Setup (one-time):
  1. Register at https://francetravail.io/
  2. Create an app, subscribe to "Offres d'emploi v2"
  3. Copy your client_id and client_secret into a .env file (see .env.example)

Auth flow: OAuth2 client_credentials. Tokens expire after ~25 minutes; we cache
in-process and refetch on 401.

Docs: https://francetravail.io/data/api/offres-emploi
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Iterator, Optional

import requests
from pydantic import ValidationError

from .schemas import RawJobPosting

logger = logging.getLogger(__name__)

TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    "?realm=%2Fpartenaire"
)
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"


class FranceTravailClient:
    """Thin wrapper around the France Travail 'Offres d'emploi' API."""

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.environ["FT_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["FT_CLIENT_SECRET"]
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # -- auth --
    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        logger.info("Fetching new France Travail access token")
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": SCOPE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload.get("expires_in", 1500)
        return self._token

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    # -- search --
    def search(
        self,
        keywords: str,
        *,
        page_size: int = 100,
        max_results: int = 500,
    ) -> Iterator[dict]:
        """
        Paginate search results. API uses a 'range' header (0-149, 150-299, ...).
        Max 150 per page; we chunk accordingly.

        Yields raw dicts from the API. Use parse_posting() to normalize.
        """
        fetched = 0
        start = 0
        # API caps ranges at 150 items per request
        chunk = min(page_size, 149)

        while fetched < max_results:
            end = start + chunk
            headers = {
                **self._auth_headers(),
                "Range": f"offres {start}-{end}",
                "Accept": "application/json",
            }
            params = {"motsCles": keywords}
            resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
            if resp.status_code == 401:
                # token probably expired mid-run; retry once
                self._token = None
                headers["Authorization"] = f"Bearer {self._get_token()}"
                resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
            if resp.status_code == 204:
                logger.info("No more results from France Travail")
                return
            resp.raise_for_status()

            page = resp.json().get("resultats", [])
            if not page:
                return
            for row in page:
                yield row
                fetched += 1
                if fetched >= max_results:
                    return

            if len(page) < chunk + 1:  # last page
                return
            start = end + 1
            # polite pause — the API is rate-limited
            time.sleep(0.5)

    # -- normalization --
    @staticmethod
    def to_raw_posting(item: dict) -> Optional[RawJobPosting]:
        """
        Map a France Travail 'resultats[i]' dict to our normalized schema.
        Returns None if the row is unusable (missing required fields).
        """
        try:
            return RawJobPosting(
                source="france_travail",
                source_job_id=item["id"],
                source_url=f"https://candidat.francetravail.fr/offres/recherche/detail/{item['id']}",
                scraped_at=datetime.now(timezone.utc),
                title=item.get("intitule", "").strip(),
                company=(item.get("entreprise") or {}).get("nom"),
                location=(item.get("lieuTravail") or {}).get("libelle"),
                country="FR",
                description=item.get("description", "").strip(),
                posted_at=_parse_iso(item.get("dateCreation")),
                contract_type=item.get("typeContrat"),
                experience_level=item.get("experienceLibelle"),
                raw_payload=item,
            )
        except (KeyError, ValidationError) as e:
            logger.warning(f"Could not parse posting {item.get('id')}: {e}")
            return None


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # France Travail returns ISO 8601 strings
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# -- CLI entry point for smoke-testing --
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = FranceTravailClient()
    # Quick smoke test: fetch 5 "data engineer" postings
    for i, row in enumerate(client.search("data engineer", max_results=5)):
        posting = client.to_raw_posting(row)
        if posting:
            print(f"[{i}] {posting.title} @ {posting.company} — {posting.location}")
