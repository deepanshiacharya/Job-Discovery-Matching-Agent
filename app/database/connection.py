import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.database.models import Base

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None


def get_engine():
    global engine, SessionLocal
    if engine is not None:
        return engine

    # First attempt: Primary DATABASE_URL (typically PostgreSQL)
    try:
        logger.info(f"Connecting to primary database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
        candidate_engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3} if "postgres" in settings.DATABASE_URL else {}
        )
        with candidate_engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        engine = candidate_engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Successfully connected to primary database.")
        return engine
    except Exception as e:
        if settings.SQLITE_FALLBACK:
            sqlite_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
            logger.warning(
                f"Primary database connection failed ({e}). "
                f"Falling back to local SQLite: {sqlite_url}"
            )
            engine = create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False}
            )
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            return engine
        else:
            logger.error(f"Database connection error and fallback disabled: {e}")
            raise


def init_db():
    eng = get_engine()
    Base.metadata.create_all(bind=eng)
    logger.info("Database schema initialized successfully.")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        get_engine()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
