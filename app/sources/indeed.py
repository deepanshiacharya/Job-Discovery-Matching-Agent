import logging
from typing import List, Optional
from app.matching.schema import RawJob
from app.sources.base import JobSource
from app.sources.mock_source import MockJobSource

logger = logging.getLogger(__name__)


class IndeedSource(JobSource):
    """Indeed source adapter. Adheres to permitted access mechanisms."""

    def __init__(self, name: str = "Indeed"):
        super().__init__(name=name)
        self._fallback = MockJobSource(name=name, filter_source="Indeed")

    def fetch_raw_jobs(self, query: Optional[str] = None, limit: int = 50) -> List[RawJob]:
        logger.info("Indeed adapter querying permitted feed/mock data...")
        return self._fallback.fetch_raw_jobs(query=query, limit=limit)
