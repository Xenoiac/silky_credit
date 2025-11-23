import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)


def _create_engine_with_fallback():
    """Create a SQLAlchemy engine and fall back to local SQLite if unavailable."""

    def _try_engine(url: str):
        engine_candidate = create_engine(url, future=True)
        with engine_candidate.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine_candidate

    primary_url = settings.db_url
    try:
        return _try_engine(primary_url)
    except Exception as exc:  # noqa: BLE001
        fallback_url = "sqlite:///./silky_credit.db"
        logger.warning(
            "Primary DB_URL '%s' unavailable (%s). Falling back to %s",
            primary_url,
            exc,
            fallback_url,
        )
        settings.db_url = fallback_url
        return _try_engine(fallback_url)


engine = _create_engine_with_fallback()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
