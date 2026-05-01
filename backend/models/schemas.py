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


class CompanyReport(BaseModel):
    company_name: str
    headquarters: Optional[str] = None
    business_units: List[str] = []
    products_and_services: List[str] = []
    target_industries: List[str] = []
    leadership: List[ExecutiveSignal] = []
    strategic_initiatives: List[StrategicInitiative] = []
    evidence_links: List[EvidenceLink] = []
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
