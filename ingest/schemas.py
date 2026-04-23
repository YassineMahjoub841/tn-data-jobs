"""Shared Pydantic schemas for raw job postings."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


class RawPosting(BaseModel):
    """A single raw job posting as emitted by any ingestor."""

    source: str  # "tanitjobs" | "france_travail"
    source_id: str  # Unique ID within the source
    url: HttpUrl
    title: str
    company_name: str
    location: Optional[str] = None
    contract_type: Optional[str] = None  # CDI, CDD, Freelance, …
    description: str
    posted_date: Optional[date] = None
    scraped_at: date

    @field_validator("title", "company_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class RawCompany(BaseModel):
    """Minimal company record extracted alongside a posting."""

    name: str
    sector: Optional[str] = None
    size: Optional[str] = None
    website: Optional[HttpUrl] = None
