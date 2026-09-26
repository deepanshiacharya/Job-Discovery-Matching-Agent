import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    PROFILE_PATH: str = Field(default="config/candidate_profile.json")
    DATA_DIR: str = Field(default="data")
    REPORT_DIR: str = Field(default="reports")

    # Database Settings
    DATABASE_URL: str = Field(default="postgresql+psycopg2://postgres:postgres@localhost:5432/job_agent")
    SQLITE_FALLBACK: bool = Field(default=True)
    SQLITE_DB_PATH: str = Field(default="job_agent.db")

    # LLM Settings
    LLM_PROVIDER: str = Field(default="mock")  # mock | ollama | openai
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_API_KEY: str = Field(default="")
    LLM_BASE_URL: str = Field(default="")

    # Email Settings
    EMAIL_PROVIDER: str = Field(default="mock")  # mock | smtp
    EMAIL_HOST: str = Field(default="smtp.gmail.com")
    EMAIL_PORT: int = Field(default=587)
    EMAIL_USERNAME: str = Field(default="")
    EMAIL_PASSWORD: str = Field(default="")
    EMAIL_FROM: str = Field(default="jobagent@example.com")
    RECIPIENT_EMAIL: str = Field(default="candidate@example.com")

    # Application Behavior
    LOG_LEVEL: str = Field(default="INFO")
    ENABLE_SEMANTIC_EMBEDDINGS: bool = Field(default=False)
    MAX_JOBS_PER_SOURCE: int = Field(default=50)

    def get_absolute_profile_path(self) -> Path:
        p = Path(self.PROFILE_PATH)
        return p if p.is_absolute() else self.BASE_DIR / p

    def get_absolute_report_dir(self) -> Path:
        p = Path(self.REPORT_DIR)
        d = p if p.is_absolute() else self.BASE_DIR / p
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_absolute_data_dir(self) -> Path:
        p = Path(self.DATA_DIR)
        return p if p.is_absolute() else self.BASE_DIR / p


settings = Settings()
