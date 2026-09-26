import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from app.matching.schema import RawJob

logger = logging.getLogger(__name__)


class JobSource(ABC):
    """Abstract base class for all job ingestion sources."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_raw_jobs(self, query: Optional[str] = None, limit: int = 50) -> List[RawJob]:
        """Fetch raw job listings from the source.

        Must handle all network/API/parsing errors internally and return
        an empty list or partial list without crashing the host process.
        """
        pass

    def discover_jobs(self, query: Optional[str] = None, limit: int = 50) -> List[RawJob]:
        """Safe wrapper around fetch_raw_jobs with comprehensive error handling."""
        try:
            logger.info(f"Querying job source: {self.name}")
            jobs = self.fetch_raw_jobs(query=query, limit=limit)
            logger.info(f"Source [{self.name}] successfully retrieved {len(jobs)} jobs.")
            return jobs
        except Exception as e:
            logger.error(f"Error querying job source [{self.name}]: {e}", exc_info=True)
            return []
