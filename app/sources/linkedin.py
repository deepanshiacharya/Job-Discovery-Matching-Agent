import logging
from typing import List, Optional
from app.matching.schema import RawJob
from app.sources.base import JobSource
from app.sources.mock_source import MockJobSource

logger = logging.getLogger(__name__)


class LinkedInSource(JobSource):
    """LinkedIn source adapter. Uses permitted mock/public feed in Phase 1 without bypassing auth or anti-bot."""

    def __init__(self, name: str = "LinkedIn"):
        super().__init__(name=name)
        self._fallback = MockJobSource(name=name, filter_source="LinkedIn")

    def fetch_raw_jobs(self, query: Optional[str] = None, limit: int = 50) -> List[RawJob]:
        logger.info("LinkedIn adapter querying permitted feed/mock data...")
        return self._fallback.fetch_raw_jobs(query=query, limit=limit)
