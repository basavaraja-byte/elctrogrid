"""Pytest fixtures providing an isolated test database and FastAPI TestClient."""

from collections.abc import Generator
import os

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401

# Use TEST_DATABASE_URL if explicitly set to PostgreSQL; otherwise use an isolated in-memory SQLite DB
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

if TEST_DB_URL.startswith("sqlite"):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(test_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    test_engine = create_engine(TEST_DB_URL, pool_pre_ping=True, future=True)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh isolated database schema for each test function."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient wired to the isolated test db_session."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()

