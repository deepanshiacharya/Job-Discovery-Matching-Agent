from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    NOT_APPLIED = "NOT_APPLIED"
    SAVED = "SAVED"
    APPLIED = "APPLIED"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class MatchCategory(str, Enum):
    HIGH_MATCH = "HIGH_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    STRETCH = "STRETCH"
    LOW_MATCH = "LOW_MATCH"


class WorkMode(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ONSITE = "On-site"
    UNKNOWN = "Unknown"


# --- Candidate Profile Models ---

class EducationItem(BaseModel):
    degree: str
    field: str = ""
    institution: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    status: str = "Completed"


class ExperienceItem(BaseModel):
    title: str
    company: str
    duration: str = ""
    description: str = ""


class ExperiencePreference(BaseModel):
    min_years: float = 0.0
    max_years: float = 3.0
    tolerance_years: float = 1.5


class ScoreWeights(BaseModel):
    role_relevance: float = 0.25
    skills_match: float = 0.25
    experience_match: float = 0.20
    education_match: float = 0.10
    location_work_mode: float = 0.10
    seniority: float = 0.05
    freshness: float = 0.05


class ScoreThresholds(BaseModel):
    HIGH_MATCH: float = 85.0
    GOOD_MATCH: float = 70.0
    STRETCH: float = 55.0


class CandidateProfile(BaseModel):
    name: str = "Candidate"
    email: str = "candidate@example.com"
    phone: str = ""
    approx_experience_years: float = 1.5
    experience_preference: ExperiencePreference = Field(default_factory=ExperiencePreference)
    education: List[EducationItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    location_preferences: List[str] = Field(default_factory=list)
    work_modes: List[str] = Field(default_factory=lambda: ["Remote", "Hybrid", "On-site"])
    scoring_weights: ScoreWeights = Field(default_factory=ScoreWeights)
    score_thresholds: ScoreThresholds = Field(default_factory=ScoreThresholds)


# --- Job Representation Models ---

class RawJob(BaseModel):
    source: str
    source_job_id: str = ""
    title: str
    company: str
    location: str = ""
    work_mode: str = "Unknown"
    description: str = ""
    experience_required: str = ""
    education_required: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    salary: str = ""
    posted_at: Optional[str] = None
    application_url: str = ""
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedJob(BaseModel):
    job_id: str
    source: str
    source_job_id: str
    title: str
    company: str
    location: str
    work_mode: str
    description: str
    experience_required: str
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    education_required: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    salary: str = ""
    posted_at: Optional[datetime] = None
    application_url: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class CanonicalJob(BaseModel):
    canonical_id: str
    title: str
    company: str
    location: str
    work_mode: str
    description: str
    experience_required: str
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    education_required: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    salary: str = ""
    posted_at: Optional[datetime] = None
    application_url: str
    sources: List[str] = Field(default_factory=list)
    source_job_ids: Dict[str, str] = Field(default_factory=dict)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)


# --- Match & Scoring Models ---

class ScoreBreakdown(BaseModel):
    role_score: float = 0.0
    skill_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    location_score: float = 0.0
    seniority_score: float = 0.0
    freshness_score: float = 0.0
    total_relevance_score: float = 0.0


class JobMatch(BaseModel):
    job: CanonicalJob
    relevance_score: float
    category: MatchCategory
    score_breakdown: ScoreBreakdown
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    why_matches: List[str] = Field(default_factory=list)
    potential_gaps: List[str] = Field(default_factory=list)
    application_status: ApplicationStatus = ApplicationStatus.NOT_APPLIED


# --- Pipeline Tracking Models ---

class PipelineRunStats(BaseModel):
    run_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    jobs_discovered: int = 0
    jobs_normalized: int = 0
    jobs_deduplicated: int = 0
    jobs_matched: int = 0
    jobs_recommended: int = 0
    high_matches: int = 0
    good_matches: int = 0
    stretch_matches: int = 0
    report_path: Optional[str] = None
    email_sent: bool = False
    status: str = "RUNNING"
    error_message: Optional[str] = None
