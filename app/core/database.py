from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

settings = get_settings()
url = settings.sqlalchemy_url

engine_options: dict = {"pool_pre_ping": True}
if url.get_backend_name() == "sqlite":
    engine_options.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine_options.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=1800,
    )

engine = create_engine(url, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
