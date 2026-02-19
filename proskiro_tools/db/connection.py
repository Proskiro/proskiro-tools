import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()


def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables."""
    return (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB')}"
    )


def create_db_engine(database_url: str | None = None, ssl_enabled: bool = True) -> Engine:
    """
    Create a SQLAlchemy engine with optional SSL configuration.
    
    Args:
        database_url: Optional database URL. If not provided, uses environment variables.
        ssl_enabled: Whether to enable SSL verification (default True for production).
    """
    url = database_url or get_database_url()
    
    connect_args = {}
    if ssl_enabled:
        ssl_rootcert = os.getenv("SSL_ROOTCERT")
        if ssl_rootcert:
            connect_args = {
                "sslmode": "verify-full",
                "sslrootcert": ssl_rootcert,
            }
    
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


# Lazy-initialized engine and session factory
_engine = None
_session_factory = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def SessionLocal() -> Session:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=_get_engine(), autocommit=False, autoflush=False)
    return _session_factory()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
