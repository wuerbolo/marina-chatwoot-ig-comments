import os

os.environ.setdefault("META_APP_ID", "test-app-id")
os.environ.setdefault("META_APP_SECRET", "test-app-secret")
os.environ.setdefault("META_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("IG_LONG_LIVED_ACCESS_TOKEN", "test-ig-token")
os.environ.setdefault("CHATWOOT_BASE_URL", "https://chatwoot.example.com")
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "1")
os.environ.setdefault("CHATWOOT_API_ACCESS_TOKEN", "test-cw-token")
os.environ.setdefault("CHATWOOT_INBOX_ID_COMENTARIOS", "1")
os.environ.setdefault("CHATWOOT_WEBHOOK_SECRET", "test-cw-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app import models  # noqa: F401


@pytest.fixture
def db_session_factory(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr("app.db.SessionLocal", session_local)
    monkeypatch.setattr("app.db.get_session", session_local)
    monkeypatch.setattr("app.services.reply_service.get_session", session_local)
    monkeypatch.setattr("app.services.comment_service.get_session", session_local)

    return session_local
