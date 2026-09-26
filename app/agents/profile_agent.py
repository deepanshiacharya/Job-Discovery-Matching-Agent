import json
import logging
from pathlib import Path
from typing import Optional
from app.config import settings
from app.matching.schema import CandidateProfile

logger = logging.getLogger(__name__)


class ProfileAgent:
    """Loads, validates, and normalizes candidate profile configuration."""

    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = profile_path or str(settings.get_absolute_profile_path())

    def load_profile(self) -> CandidateProfile:
        path = Path(self.profile_path)
        logger.info(f"Loading candidate profile from: {path}")

        if not path.exists():
            logger.warning(f"Profile path {path} does not exist. Using default profile instance.")
            return CandidateProfile()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        profile = CandidateProfile(**data)
        logger.info(f"Loaded profile for: {profile.name} with {len(profile.technical_skills)} skills and {len(profile.target_roles)} target roles.")
        return profile
