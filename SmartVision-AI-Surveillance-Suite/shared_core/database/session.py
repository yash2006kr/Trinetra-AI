"""Database engine/session helpers for SQLite and PostgreSQL."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared_core.database.models import Base


def ensure_sqlite_parent(database_url: str) -> None:
    if database_url.startswith("sqlite:///"):
        path = Path(database_url.replace("sqlite:///", "", 1))
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    ensure_sqlite_parent(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
