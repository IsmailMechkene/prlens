"""Enabling a repo must not claim success when GitHub will send it nothing.

Enabling writes an Installation row and nothing else. Reviews only ever arrive if
the PRLens GitHub App is *also* installed on the account that owns the repo — a
step only that account's owner can perform. A user who signed in with a second
GitHub account, enabled a repo on it and waited for a review that never came is the
bug these tests pin down: /enable now reports whether the App is really there.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import get_db
from database.models import Base, Installation, User
from prlens.webhook.app import JWT_ALGORITHM, JWT_SECRET, app

REPO = "other-account/test"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def user(db_session):
    user = User(github_id=7, name="kura", handle="@kura", initials="KU")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth(user: User) -> dict[str, str]:
    token = pyjwt.encode(
        {"user_id": user.id, "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def enable(user: User, installed: bool | None, slug: str | None = "prlens-reviewer"):
    with patch("prlens.webhook.app.GitHubClient.is_app_installed_on", return_value=installed), \
         patch("prlens.webhook.app.GitHubClient.app_slug", return_value=slug):
        return TestClient(app).post(
            f"/api/repos/{REPO}/enable",
            json={"owner": "other-account", "visibility": "Public"},
            headers=auth(user),
        )


def test_enable_flags_a_repo_whose_account_has_not_installed_the_app(db_session, user):
    response = enable(user, installed=False)

    assert response.status_code == 200
    body = response.json()
    assert body["appInstalled"] is False
    assert body["installUrl"] == "https://github.com/apps/prlens-reviewer/installations/new"

    # The row is still written: the repo is enabled, it is just not yet reachable.
    assert db_session.query(Installation).filter(Installation.repo_name == REPO).count() == 1


def test_enable_reports_an_installed_app(db_session, user):
    body = enable(user, installed=True).json()

    assert body["appInstalled"] is True
    assert body["installUrl"] is None


def test_enable_does_not_claim_the_app_is_missing_when_the_check_failed(db_session, user):
    # None is "could not tell". Reporting False here would send a user with a
    # perfectly good installation off to reinstall it.
    body = enable(user, installed=None).json()

    assert body["appInstalled"] is None
    assert body["installUrl"] is None
