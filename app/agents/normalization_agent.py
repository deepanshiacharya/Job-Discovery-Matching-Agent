import hashlib
import logging
from datetime import datetime
from typing import List
from app.matching.schema import RawJob, NormalizedJob
from app.matching.rules import parse_experience_range, parse_posted_date

logger = logging.getLogger(__name__)


class JobNormalizationAgent:
    """Standardizes heterogeneous raw job listings into canonical NormalizedJob models."""

    def _generate_job_id(self, raw: RawJob) -> str:
        # Generate deterministic unique ID based on source and source_job_id or url
        seed = f"{raw.source}:{raw.source_job_id}:{raw.company}:{raw.title}:{raw.application_url}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return " ".join(text.split()).strip()

    def normalize_single(self, raw: RawJob) -> NormalizedJob:
        min_exp, max_exp = parse_experience_range(raw.experience_required)
        posted_dt = parse_posted_date(raw.posted_at)

        # Detect work mode if unspecified
        work_mode = raw.work_mode or "Unknown"
        combined_text = f"{raw.title} {raw.location} {raw.description}".lower()
        if work_mode in ("Unknown", ""):
            if "remote" in combined_text:
                work_mode = "Remote"
            elif "hybrid" in combined_text:
                work_mode = "Hybrid"
            elif "on-site" in combined_text or "onsite" in combined_text or "in office" in combined_text:
                work_mode = "On-site"

        return NormalizedJob(
            job_id=self._generate_job_id(raw),
            source=raw.source,
            source_job_id=raw.source_job_id,
            title=self._clean_text(raw.title),
            company=self._clean_text(raw.company),
            location=self._clean_text(raw.location),
            work_mode=work_mode,
            description=raw.description.strip(),
            experience_required=raw.experience_required.strip(),
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            education_required=raw.education_required.strip(),
            required_skills=list(dict.fromkeys([s.strip() for s in raw.required_skills if s.strip()])),
            preferred_skills=list(dict.fromkeys([s.strip() for s in raw.preferred_skills if s.strip()])),
            salary=raw.salary.strip(),
            posted_at=posted_dt,
            application_url=raw.application_url.strip(),
            scraped_at=datetime.utcnow()
        )

    def normalize_all(self, raw_jobs: List[RawJob]) -> List[NormalizedJob]:
        normalized = []
        for raw in raw_jobs:
            try:
                nj = self.normalize_single(raw)
                normalized.append(nj)
            except Exception as e:
                logger.error(f"Failed to normalize job [{raw.title} from {raw.source}]: {e}. Skipping.", exc_info=True)

        logger.info(f"Normalized {len(normalized)} of {len(raw_jobs)} raw jobs.")
        return normalized
