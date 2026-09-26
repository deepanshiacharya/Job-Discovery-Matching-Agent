from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from app.matching.schema import (
    CandidateProfile,
    RawJob,
    NormalizedJob,
    CanonicalJob,
    JobMatch,
    PipelineRunStats
)


class JobAgentState(TypedDict, total=False):
    candidate_profile: Optional[CandidateProfile]
    raw_jobs: List[RawJob]
    normalized_jobs: List[NormalizedJob]
    deduplicated_jobs: List[CanonicalJob]
    filtered_out_jobs: List[CanonicalJob]
    scored_matches: List[JobMatch]
    ranked_matches: List[JobMatch]
    top_recommendations: List[JobMatch]
    stats: PipelineRunStats
    report_path: Optional[str]
    email_sent: bool
    errors: List[str]
