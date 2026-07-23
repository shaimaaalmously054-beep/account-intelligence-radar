"""
Data models for Account Intelligence Radar.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InputMode(str, Enum):
    COMPANY = "company"
    GEOGRAPHY = "geography"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CompanyRequest(BaseModel):
    company_name: str = Field(..., min_length=1, description="Target company name")
    objective_prompt: str = Field(
        default=(
            "Extract headquarters, business units, core products, target industries, "
            "key executives, and recent strategic initiatives. Return structured JSON."
        ),
        description="Extraction objective for the LLM",
    )


class GeographyRequest(BaseModel):
    location: str = Field(..., description="City/country or country/sector keywords")
    target_criteria: str = Field(..., description="e.g. 'manufacturing, energy, logistics'")
    objective_prompt: str = Field(
        default=(
            "Identify top companies matching the criteria, then extract headquarters, "
            "business units, core products, target industries, key executives, and "
            "recent strategic initiatives. Return structured JSON."
        )
    )
    top_n: int = Field(default=3, ge=1, le=10, description="Number of companies to deep-dive")


class JobCreateRequest(BaseModel):
    mode: InputMode
    company: Optional[CompanyRequest] = None
    geography: Optional[GeographyRequest] = None


# ---------------------------------------------------------------------------
# Output / report models
# ---------------------------------------------------------------------------

class ExecutiveSignal(BaseModel):
    name: str
    title: str
    source_url: Optional[str] = None


class StrategicInitiative(BaseModel):
    description: str
    category: Optional[str] = None  # e.g. AI, ERP, Expansion
    source_url: Optional[str] = None


class EvidenceLink(BaseModel):
    url: str
    description: Optional[str] = None


class SourceRecord(BaseModel):
    id: str
    title: Optional[str] = None
    url: str
    original_url: Optional[str] = None
    domain: str
    publisher: Optional[str] = None
    author: Optional[str] = None
    snippet: Optional[str] = None
    extracted_text: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    source_type: str = "Other"
    search_query: Optional[str] = None
    rank: Optional[int] = None
    relevance_score: Optional[float] = None
    extraction_status: str = "search_only"
    evidence: List[str] = Field(default_factory=list)


class CompanyReport(BaseModel):
    company_name: str
    headquarters: Optional[str] = None
    business_units: List[str] = Field(default_factory=list)
    products_and_services: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    leadership: List[ExecutiveSignal] = Field(default_factory=list)
    strategic_initiatives: List[StrategicInitiative] = Field(default_factory=list)
    evidence_links: List[EvidenceLink] = Field(default_factory=list)
    search_results: List[SourceRecord] = Field(default_factory=list)
    raw_extraction: Optional[Dict[str, Any]] = None
    linkedin_search_suggestion: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    mode: InputMode
    created_at: str
    updated_at: str
    result: Optional[List[CompanyReport]] = None
    error: Optional[str] = None
    report_paths: Optional[Dict[str, str]] = None
    stage: Optional[str] = None
    query: Optional[str] = None
    source_count: int = 0
    report_ids: List[str] = Field(default_factory=list)
    comparison_id: Optional[str] = None
    previous_scan_date: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=10, max_length=128)


class AuthRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
