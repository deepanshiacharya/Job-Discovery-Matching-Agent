import logging
from typing import List
from app.matching.schema import RawJob
from app.sources.base import JobSource
from app.sources.mock_source import MockJobSource
from app.sources.linkedin import LinkedInSource
from app.sources.indeed import IndeedSource
from app.sources.naukri import NaukriSource

logger = logging.getLogger(__name__)


class JobDiscoveryAgent:
    """Discovers job openings across configured job sources with error isolation."""

    def __init__(self, sources: List[JobSource] = None):
        if sources is None:
            # Default configured sources for discovery
            self.sources = [
                LinkedInSource(),
                IndeedSource(),
                NaukriSource(),
                MockJobSource(name="CompanyCareers")
            ]
        else:
            self.sources = sources

    def discover_all(self, query: str = None, limit_per_source: int = 50) -> List[RawJob]:
        all_raw_jobs = []
        for source in self.sources:
            try:
                jobs = source.discover_jobs(query=query, limit=limit_per_source)
                all_raw_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Source [{source.name}] discovery failed unexpectedly: {e}. Skipping source.", exc_info=True)

        logger.info(f"Discovery complete. Total raw jobs retrieved: {len(all_raw_jobs)}")
        return all_raw_jobs
