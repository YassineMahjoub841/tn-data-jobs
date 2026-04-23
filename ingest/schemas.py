"""
Shared schema for a normalized raw job posting.

Every source (scraper or API) normalizes to this shape before landing in raw.jobs.
The point is: the warehouse sees one shape regardless of source, but we preserve
enough source-specific metadata to debug and re-ingest.

Keep this minimal. Fields you're not sure about go in `raw_payload`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class RawJobPosting(BaseModel):
    """
    One job posting from one source, normalized.

    IDs: we do NOT trust source-side IDs across refreshes — a stable ID is
    (source, source_job_id). Use that when deduplicating.
    """

    # --- Provenance ---
    source: str = Field(..., description="E.g. 'tanitjobs', 'france_travail'")
    source_job_id: str = Field(..., description="The ID the source uses")
    source_url: HttpUrl = Field(..., description="Canonical posting URL")
    scraped_at: datetime = Field(..., description="When we fetched this, UTC")

    # --- Core fields ---
    title: str
    company: Optional[str] = None
    location: Optional[str] = None  # Free text; we'll geocode downstream
    country: Optional[str] = None   # ISO-2: 'TN', 'FR', etc.
    description: str = Field(..., description="Full JD text, raw")
    posted_at: Optional[datetime] = None

    # --- Optional structured hints from source ---
    contract_type: Optional[str] = None   # 'CDI', 'CDD', 'Internship', 'Freelance'
    experience_level: Optional[str] = None  # Source's own label, we don't harmonize yet
    remote: Optional[str] = None           # 'remote', 'hybrid', 'on-site', None if unknown

    # --- Everything else ---
    raw_payload: dict = Field(
        default_factory=dict,
        description="Source-specific fields we don't normalize. Store liberally.",
    )

    def to_bq_row(self) -> dict:
        """Flatten for BigQuery insert. JSON-encode the raw payload."""
        import json
        d = self.model_dump(mode="json")
        d["raw_payload"] = json.dumps(d["raw_payload"], ensure_ascii=False)
        return d
