"""Tests for the non-admin free-review cap.

Three surfaces are covered:

* ``_review_limit_reached`` — the gate ``run_agent`` consults before it builds any
  client or spends an LLM call. It reads the owner's ``reviews_used`` counter.
* ``_persist_review`` — charges a completed review against that counter, in the
  same transaction as the rows it writes.
* ``GET /api/stats`` — carries ``reviewLimit`` (built from ``reviews_used``) so the
  dashboard can show usage; ``null`` for an exempt admin.

The gate and persist both run on a background worker, so they reach the database
through ``_background_session_factory`` rather than the request session; the tests
point that factory at the same in-memory database.
"""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import get_db
from database.models import ROLE_ADMIN, ROLE_USER, Base, Installation, User
from prlens.models.review import ReviewResult
from prlens.webhook import app as webhook_app
from prlens.webhook.app import (
    JWT_ALGORITHM,
    JWT_SECRET,
    NON_ADMIN_REVIEW_LIMIT,
    _persist_review,
    _review_limit_reached,
    app,
)


@pytest.fixture
def engine():
    """A fresh in-memory database shared across every connection (StaticPool)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(engine):
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


def make_user(db, github_id, login, role=ROLE_USER, used=0):
    user = User(
        github_id=github_id,
        name=login,
        handle=f"@{login}",
        initials=login[:2].upper(),
        role=role,
        reviews_used=used,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_installation(db, user, repo_name, active=True):
    installation = Installation(
        user_id=user.id,
        repo_name=repo_name,
        owner=repo_name.split("/")[0],
        visibility="Private",
        connected=True,
        active=active,
        min_severity="info",
        languages=["python"],
        approve_threshold=80,
        changes_threshold=50,
        excluded_files=[],
        reviewer_map={},
    )
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation


def auth(user):
    token = pyjwt.encode(
        {"user_id": user.id, "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def use_background_db(engine, monkeypatch):
    """Point the background-session factory at the test database.

    The gate and _persist_review run on a worker thread in production, so they do
    not use the request-scoped session; this makes the thread's factory resolve to
    the same in-memory engine the fixtures write to.
    """
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(webhook_app, "_background_session_factory", lambda: factory)


# ---------------------------------------------------------------------------
# The gate: _review_limit_reached
# ---------------------------------------------------------------------------

def test_limit_not_reached_below_the_cap(db_session, use_background_db):
    user = make_user(db_session, 1, "tester", used=NON_ADMIN_REVIEW_LIMIT - 1)
    make_installation(db_session, user, "tester/repo")

    assert _review_limit_reached("tester/repo") is False


def test_limit_reached_at_the_cap(db_session, use_background_db):
    user = make_user(db_session, 1, "tester", used=NON_ADMIN_REVIEW_LIMIT)
    make_installation(db_session, user, "tester/repo")

    assert _review_limit_reached("tester/repo") is True


def test_admin_owner_is_never_capped(db_session, use_background_db):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN, used=NON_ADMIN_REVIEW_LIMIT + 5)
    make_installation(db_session, admin, "boss/repo")

    assert _review_limit_reached("boss/repo") is False


def test_shared_repo_allowed_while_one_owner_has_budget(db_session, use_background_db):
    """A repo two people connected is only blocked when *both* are capped."""
    capped = make_user(db_session, 1, "capped", used=NON_ADMIN_REVIEW_LIMIT)
    fresh = make_user(db_session, 2, "fresh", used=0)
    make_installation(db_session, capped, "acme/api")
    make_installation(db_session, fresh, "acme/api")

    assert _review_limit_reached("acme/api") is False


def test_inactive_installations_do_not_hold_a_repo_open(db_session, use_background_db):
    """A paused installation's owner does not keep the cap from applying."""
    capped = make_user(db_session, 1, "capped", used=NON_ADMIN_REVIEW_LIMIT)
    paused = make_user(db_session, 2, "paused", used=0)
    make_installation(db_session, capped, "acme/api")
    make_installation(db_session, paused, "acme/api", active=False)

    assert _review_limit_reached("acme/api") is True


def test_unknown_repo_is_not_capped(db_session, use_background_db):
    assert _review_limit_reached("nobody/repo") is False


# ---------------------------------------------------------------------------
# The counter: _persist_review charges every active owner once
# ---------------------------------------------------------------------------

def test_persist_review_increments_reviews_used(db_session, use_background_db, sample_pr):
    user = make_user(db_session, 1, "tester", used=4)
    make_installation(db_session, user, sample_pr.repo)

    _persist_review(sample_pr.repo, sample_pr, ReviewResult(score=90), "approved")

    db_session.expire_all()
    reloaded = db_session.query(User).filter(User.id == user.id).first()
    assert reloaded.reviews_used == 5


def test_persist_review_charges_each_shared_owner(db_session, use_background_db, sample_pr):
    a = make_user(db_session, 1, "a", used=0)
    b = make_user(db_session, 2, "b", used=7)
    make_installation(db_session, a, sample_pr.repo)
    make_installation(db_session, b, sample_pr.repo)

    _persist_review(sample_pr.repo, sample_pr, ReviewResult(score=90), "approved")

    db_session.expire_all()
    assert db_session.query(User).filter(User.id == a.id).first().reviews_used == 1
    assert db_session.query(User).filter(User.id == b.id).first().reviews_used == 8


# ---------------------------------------------------------------------------
# The dashboard surface: GET /api/stats reviewLimit
# ---------------------------------------------------------------------------

def test_stats_reports_review_limit_for_a_non_admin(client, db_session):
    user = make_user(db_session, 1, "tester", used=3)

    body = client.get("/api/stats", headers=auth(user)).json()

    assert body["reviewLimit"] == {
        "used": 3,
        "limit": NON_ADMIN_REVIEW_LIMIT,
        "reached": False,
    }


def test_stats_marks_the_limit_reached_at_the_cap(client, db_session):
    user = make_user(db_session, 1, "tester", used=NON_ADMIN_REVIEW_LIMIT)

    body = client.get("/api/stats", headers=auth(user)).json()

    assert body["reviewLimit"]["used"] == NON_ADMIN_REVIEW_LIMIT
    assert body["reviewLimit"]["reached"] is True


def test_stats_exempts_admins_from_the_limit(client, db_session):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)

    body = client.get("/api/stats", headers=auth(admin)).json()

    assert body["reviewLimit"] is None
