from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator


class JobSearchQuery(BaseModel):
    """Candidate search parameters for automatic job discovery."""
    role: str = Field(..., min_length=2, max_length=255, description="Target job title or role keyword")
    location: Optional[str] = Field(None, max_length=255, description="Geographic location preference")
    remote: Optional[bool] = Field(False, description="Filter for remote opportunities")
    experience: Optional[str] = Field(None, description="Experience level e.g. '0-2 years', 'entry', 'mid'")
    employment_type: Optional[str] = Field(None, description="full-time, contract, internship, etc.")
    salary_min: Optional[float] = Field(None, ge=0)
    salary_max: Optional[float] = Field(None, ge=0)
    skills: List[str] = Field(default_factory=list, description="Explicit skills to target")
    keywords: List[str] = Field(default_factory=list, description="Additional search keywords")
    posted_within_days: Optional[int] = Field(14, ge=1, le=90, description="Recency limit in days")
    resume_id: Optional[uuid.UUID] = Field(None, description="Target resume ID to match against")
    limit: Optional[int] = Field(50, ge=1, le=100, description="Maximum listings to fetch")


class RawJobListing(BaseModel):
    """Raw, un-normalized job listing produced by a source adapter."""
    external_id: Optional[str] = None
    source: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    description: str
    url: Optional[str] = None
    posted_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NormalizedJobListing(BaseModel):
    """Sanitized, standardized job listing ready for analysis and deduplication."""
    external_id: Optional[str] = None
    source: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None  # "remote", "hybrid", "on-site", "unknown"
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    description: str
    url: Optional[str] = None
    posted_at: Optional[datetime] = None
    collected_at: datetime
    dedup_hash: str


class MissingSkillDetail(BaseModel):
    skill_name: str
    category: Optional[str] = "General"
    priority: str = "medium"  # high, medium, low


class RankedJobOpportunity(BaseModel):
    """Fully analyzed, scored, and ranked job result for presentation."""
    job_id: uuid.UUID
    listing_id: uuid.UUID
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    source: str
    url: Optional[str] = None
    posted_at: Optional[str] = None
    description_snippet: str
    
    # Deterministic match scores (0-100)
    overall_match_score: float
    skill_score: float
    keyword_score: float
    semantic_score: float
    experience_score: float
    education_score: float
    rank_score: float
    rank: int

    # Explainability breakdown
    matched_skills: List[str] = []
    missing_skills: List[MissingSkillDetail] = []
    partial_matches: List[str] = []
    ai_explanation: Optional[str] = None

    # Application state
    is_saved: bool = False
    application_status: str = "discovered"  # discovered, saved, applied, interview, rejected, offer


class SearchStatusResponse(BaseModel):
    """Asynchronous search job status."""
    search_id: uuid.UUID
    status: str  # queued, searching, analyzing, matching, completed, failed
    jobs_found: int = 0
    jobs_analyzed: int = 0
    jobs_matched: int = 0
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class SearchResultsResponse(BaseModel):
    """Paginated or complete ranked search results."""
    search_id: uuid.UUID
    query: Dict[str, Any]
    status: str
    total_results: int
    results: List[RankedJobOpportunity]


class SearchListItem(BaseModel):
    id: uuid.UUID
    query_role: str
    location: Optional[str]
    remote: Optional[bool]
    status: str
    jobs_found: int
    jobs_matched: int
    created_at: str


class SavedJobResponse(BaseModel):
    id: uuid.UUID
    job_listing_id: uuid.UUID
    title: str
    company: Optional[str]
    location: Optional[str]
    remote_type: Optional[str]
    source: str
    url: Optional[str]
    status: str
    notes: Optional[str]
    created_at: str
    updated_at: str


class SearchDefaultsResponse(BaseModel):
    target_role: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    experience_level: Optional[str] = None
    skills: List[str] = []
    recommended_resume_id: Optional[uuid.UUID] = None
    recommended_resume_name: Optional[str] = None
