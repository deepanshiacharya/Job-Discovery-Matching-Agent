import json
import logging
from pathlib import Path
from typing import List, Optional
from app.config import settings
from app.matching.schema import RawJob
from app.sources.base import JobSource

logger = logging.getLogger(__name__)


class MockJobSource(JobSource):
    """Job source backed by a local JSON file for deterministic testing and development."""

    def __init__(self, name: str = "MockSource", file_path: Optional[str] = None, filter_source: Optional[str] = None):
        super().__init__(name=name)
        self.file_path = file_path or str(settings.get_absolute_data_dir() / "sample_jobs.json")
        self.filter_source = filter_source

    def fetch_raw_jobs(self, query: Optional[str] = None, limit: int = 50) -> List[RawJob]:
        path = Path(self.file_path)
        if not path.exists():
            logger.warning(f"Mock jobs file not found at: {path}")
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_jobs = []
        for item in data:
            if self.filter_source and item.get("source", "").lower() != self.filter_source.lower():
                continue

            raw_job = RawJob(
                source=item.get("source", self.name),
                source_job_id=item.get("source_job_id", ""),
                title=item.get("title", ""),
                company=item.get("company", ""),
                location=item.get("location", ""),
                work_mode=item.get("work_mode", "Unknown"),
                description=item.get("description", ""),
                experience_required=item.get("experience_required", ""),
                education_required=item.get("education_required", ""),
                required_skills=item.get("required_skills", []),
                preferred_skills=item.get("preferred_skills", []),
                salary=item.get("salary", ""),
                posted_at=item.get("posted_at"),
                application_url=item.get("application_url", ""),
                extra_metadata=item.get("extra_metadata", {})
            )
            raw_jobs.append(raw_job)

            if len(raw_jobs) >= limit:
                break

        return raw_jobs
