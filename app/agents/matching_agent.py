import hashlib
import logging
from typing import List, Tuple
from rapidfuzz import fuzz

from app.matching.schema import (
    CandidateProfile,
    NormalizedJob,
    CanonicalJob,
    JobMatch,
    ApplicationStatus
)
from app.matching.rules import passes_hard_filters
from app.matching.scoring import evaluate_job_relevance

logger = logging.getLogger(__name__)


class JobMatchingAgent:
    """Handles multi-signal deduplication, hard filtering, and candidate relevance scoring."""

    def __init__(self, description_sim_threshold: float = 85.0):
        self.description_sim_threshold = description_sim_threshold

    def _normalize_key(self, text: str) -> str:
        return "".join(c for c in (text or "").lower() if c.isalnum())

    def _is_duplicate(self, j1: NormalizedJob, j2: CanonicalJob) -> bool:
        """Evaluate if j1 is a duplicate of canonical job j2 using multiple signals."""
        # Signal 1: Exact URL match
        if j1.application_url and j2.application_url and j1.application_url.strip() == j2.application_url.strip():
            return True

        # Signal 2: Same source job ID under the same source
        if j1.source in j2.source_job_ids and j1.source_job_id and j2.source_job_ids[j1.source] == j1.source_job_id:
            return True

        # Signal 3: Normalized company + title + location match
        c1, c2 = self._normalize_key(j1.company), self._normalize_key(j2.company)
        t1, t2 = self._normalize_key(j1.title), self._normalize_key(j2.title)
        l1, l2 = self._normalize_key(j1.location), self._normalize_key(j2.location)

        company_match = (c1 == c2) or (fuzz.ratio(c1, c2) > 90)
        title_match = (t1 == t2) or (fuzz.token_set_ratio(t1, t2) > 90)
        loc_match = (l1 == l2) or (l1 in l2 or l2 in l1) or ("remote" in j1.work_mode.lower() and "remote" in j2.work_mode.lower())

        if company_match and title_match and loc_match:
            return True

        # Signal 4: Description similarity
        if j1.description and j2.description and len(j1.description) > 50 and len(j2.description) > 50:
            if company_match and fuzz.token_set_ratio(j1.description[:300], j2.description[:300]) > self.description_sim_threshold:
                return True

        return False

    def deduplicate(self, jobs: List[NormalizedJob]) -> List[CanonicalJob]:
        """Group and deduplicate jobs into canonical representations."""
        canonical_jobs: List[CanonicalJob] = []

        for job in jobs:
            matched_canonical = None
            for can in canonical_jobs:
                if self._is_duplicate(job, can):
                    matched_canonical = can
                    break

            if matched_canonical:
                # Merge source metadata
                if job.source not in matched_canonical.sources:
                    matched_canonical.sources.append(job.source)
                if job.source_job_id:
                    matched_canonical.source_job_ids[job.source] = job.source_job_id

                # Pick earlier posted_at or better information if available
                if job.posted_at and (not matched_canonical.posted_at or job.posted_at < matched_canonical.posted_at):
                    matched_canonical.posted_at = job.posted_at

                # Merge skills
                for s in job.required_skills:
                    if s not in matched_canonical.required_skills:
                        matched_canonical.required_skills.append(s)
                for s in job.preferred_skills:
                    if s not in matched_canonical.preferred_skills:
                        matched_canonical.preferred_skills.append(s)
            else:
                # Create new canonical job
                can_id = hashlib.sha256(
                    f"{job.company}:{job.title}:{job.location}:{job.application_url}".encode("utf-8")
                ).hexdigest()[:16]

                new_can = CanonicalJob(
                    canonical_id=can_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    work_mode=job.work_mode,
                    description=job.description,
                    experience_required=job.experience_required,
                    min_experience_years=job.min_experience_years,
                    max_experience_years=job.max_experience_years,
                    education_required=job.education_required,
                    required_skills=job.required_skills,
                    preferred_skills=job.preferred_skills,
                    salary=job.salary,
                    posted_at=job.posted_at,
                    application_url=job.application_url,
                    sources=[job.source],
                    source_job_ids={job.source: job.source_job_id} if job.source_job_id else {}
                )
                canonical_jobs.append(new_can)

        logger.info(f"Deduplication complete: {len(jobs)} normalized jobs -> {len(canonical_jobs)} canonical jobs.")
        return canonical_jobs

    def filter_and_match(
        self,
        jobs: List[CanonicalJob],
        profile: CandidateProfile,
        status_lookup_fn=None
    ) -> Tuple[List[JobMatch], List[CanonicalJob]]:
        """Apply Layer 1 hard filters and Layer 2-4 relevance evaluation."""
        matches: List[JobMatch] = []
        filtered_out: List[CanonicalJob] = []

        for job in jobs:
            # Create temporary normalized view for hard filter check
            dummy_norm = NormalizedJob(
                job_id=job.canonical_id,
                source=",".join(job.sources),
                source_job_id="",
                title=job.title,
                company=job.company,
                location=job.location,
                work_mode=job.work_mode,
                description=job.description,
                experience_required=job.experience_required,
                min_experience_years=job.min_experience_years,
                max_experience_years=job.max_experience_years,
                education_required=job.education_required,
                application_url=job.application_url
            )
            passes, reason = passes_hard_filters(dummy_norm, profile)
            if not passes:
                logger.info(f"Filtering out '{job.title}' at '{job.company}': {reason}")
                filtered_out.append(job)
                continue

            current_status = ApplicationStatus.NOT_APPLIED
            if status_lookup_fn:
                current_status = status_lookup_fn(job.canonical_id)

            match = evaluate_job_relevance(job, profile, current_status=current_status)
            matches.append(match)

        logger.info(f"Matched {len(matches)} jobs; filtered out {len(filtered_out)} jobs.")
        return matches, filtered_out
