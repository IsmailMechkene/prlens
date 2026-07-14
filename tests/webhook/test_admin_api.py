"""Tests for the admin section of the dashboard API.

These are the first tests in the suite to drive the `/api` endpoints against a real
(SQLite, in-memory) database rather than mocks: the whole point of `require_admin`
is what it does with the *stored* role, so mocking the user away would test nothing.
`get_db` is overridden to hand out sessions on that database, and `get_current_user`
is left alone — the tests mint real session JWTs, so the token-to-role path is
exercised end to end.

The security-relevant case is `test_admin_routes_reject_a_non_admin`: every admin
route must answer 403 to an ordinary — but perfectly valid — session.
"""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import get_db
from database.models import (
    ROLE_ADMIN,
    ROLE_USER,
    Base,
    Installation,
    Review,
    ReviewComment,
    User,
)
from prlens.webhook.app import JWT_ALGORITHM, JWT_SECRET, app

ADMIN_ROUTES = [
    "/api/admin/stats",
    "/api/admin/users",
    "/api/admin/installations",
    "/api/admin/reviews",
    "/api/admin/users/1",
]


@pytest.fixture
def db_session():
    """A session on a fresh in-memory database, shared with the app under test.

    StaticPool keeps every connection pointed at the same in-memory database — the
    default pool would give the request a *different*, empty one.
    """
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
def client():
    return TestClient(app)


def make_user(db, github_id: int, login: str, role: str = ROLE_USER) -> User:
    user = User(
        github_id=github_id,
        name=login,
        handle=f"@{login}",
        initials=login[:2].upper(),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_installation(db, user: User, repo_name: str, active: bool = True) -> Installation:
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


def make_review(db, installation: Installation, number: int, score: int, status: str) -> Review:
    review = Review(
        installation_id=installation.id,
        pr_number=number,
        pr_title=f"PR {number}",
        score=score,
        status=status,
        reviewed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def auth(user: User) -> dict[str, str]:
    """The Authorization header for a real session token belonging to ``user``."""
    token = pyjwt.encode(
        {"user_id": user.id, "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authorization — the reason this section exists
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route", ADMIN_ROUTES)
def test_admin_routes_reject_a_non_admin(client, db_session, route):
    """A valid session is not enough: the stored role has to say admin."""
    user = make_user(db_session, 1, "regular")

    resp = client.get(route, headers=auth(user))

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Administrator access required"


@pytest.mark.parametrize("route", ADMIN_ROUTES)
def test_admin_routes_reject_an_anonymous_caller(client, db_session, route):
    make_user(db_session, 1, "someone", role=ROLE_ADMIN)  # id 1, so the /users/1 route resolves

    resp = client.get(route)

    assert resp.status_code == 401


@pytest.mark.parametrize("route", ADMIN_ROUTES)
def test_admin_routes_accept_an_admin(client, db_session, route):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)

    resp = client.get(route, headers=auth(admin))

    assert resp.status_code == 200


def test_revoking_the_role_closes_the_door_on_an_existing_token(client, db_session):
    """The role is read from the row, not from a claim baked into the JWT.

    A 30-day token minted while the user was an admin must stop working the moment
    the role is taken away — not when the token eventually expires.
    """
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    headers = auth(admin)
    assert client.get("/api/admin/stats", headers=headers).status_code == 200

    admin.role = ROLE_USER
    db_session.commit()

    assert client.get("/api/admin/stats", headers=headers).status_code == 403


def test_role_is_exposed_on_the_user_endpoint(client, db_session):
    """The dashboard gates the admin link on this field."""
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    regular = make_user(db_session, 2, "regular")

    assert client.get("/api/user", headers=auth(admin)).json()["role"] == ROLE_ADMIN
    assert client.get("/api/user", headers=auth(regular)).json()["role"] == ROLE_USER


# ---------------------------------------------------------------------------
# The views themselves
# ---------------------------------------------------------------------------

def test_admin_stats_count_the_whole_deployment_not_just_the_caller(client, db_session):
    """The distinction that justifies the section: these totals span every user."""
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    other = make_user(db_session, 2, "regular")

    own = make_installation(db_session, admin, "acme/api")
    theirs = make_installation(db_session, other, "acme/web")
    make_installation(db_session, other, "acme/paused", active=False)

    make_review(db_session, own, 1, 90, "approved")
    make_review(db_session, theirs, 2, 40, "changes_requested")
    make_review(db_session, theirs, 3, 0, "total_failure")

    stats = {s["id"]: s for s in client.get("/api/admin/stats", headers=auth(admin)).json()["stats"]}

    assert stats["users"]["value"] == "2"
    assert stats["users"]["delta"] == "1 admin"
    assert stats["repos"]["value"] == "3"
    assert stats["repos"]["delta"] == "2 active"
    # Three reviews across two different users — the caller's own dashboard would
    # only ever have shown the one.
    assert stats["reviews"]["value"] == "3"
    assert stats["failures"]["value"] == "1"
    assert stats["failures"]["delta"] == "33% of runs"


def test_admin_stats_on_an_empty_deployment(client, db_session):
    """No reviews must not divide by zero on the failure rate."""
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)

    stats = {s["id"]: s for s in client.get("/api/admin/stats", headers=auth(admin)).json()["stats"]}

    assert stats["reviews"]["value"] == "0"
    assert stats["failures"]["value"] == "0"
    assert stats["failures"]["delta"] == ""


def test_admin_users_lists_every_account_with_its_counts(client, db_session):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    other = make_user(db_session, 2, "regular")

    installation = make_installation(db_session, other, "acme/web")
    make_review(db_session, installation, 1, 80, "approved")
    make_review(db_session, installation, 2, 70, "comment")

    users = {u["handle"]: u for u in client.get("/api/admin/users", headers=auth(admin)).json()}

    assert users["@boss"]["role"] == ROLE_ADMIN
    assert users["@boss"]["repos"] == 0
    assert users["@boss"]["reviews"] == 0
    # Never reviewed anything: an em dash, not a relative time computed from nothing.
    assert users["@boss"]["lastActive"] == "—"

    assert users["@regular"]["role"] == ROLE_USER
    assert users["@regular"]["repos"] == 1
    assert users["@regular"]["reviews"] == 2
    assert users["@regular"]["lastActive"] == "just now"


def test_admin_reviews_feed_is_global_and_tagged_with_its_user(client, db_session):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    other = make_user(db_session, 2, "regular")

    make_review(db_session, make_installation(db_session, other, "acme/web"), 7, 55, "comment")

    feed = client.get("/api/admin/reviews", headers=auth(admin)).json()

    assert len(feed) == 1
    assert feed[0]["user"] == "@regular"
    assert feed[0]["repo"] == "acme/web"
    assert feed[0]["number"] == 7


def test_admin_reviews_can_be_narrowed_to_the_failures(client, db_session):
    """`status=failed` covers both failure statuses, which is the outage signal."""
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    installation = make_installation(db_session, admin, "acme/api")

    make_review(db_session, installation, 1, 90, "approved")
    make_review(db_session, installation, 2, 0, "incomplete")
    make_review(db_session, installation, 3, 0, "total_failure")

    feed = client.get("/api/admin/reviews?status=failed", headers=auth(admin)).json()

    assert {r["status"] for r in feed} == {"incomplete", "total_failure"}


def test_admin_installations_show_duplicate_connections_of_one_repo(client, db_session):
    """The known per-user-installation duplication is visible here and nowhere else.

    Two users connecting the same repo produce two rows — which is what makes
    "toggling one inactive does not silence the other" diagnosable at all.
    """
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    other = make_user(db_session, 2, "regular")

    make_installation(db_session, admin, "acme/api", active=True)
    make_installation(db_session, other, "acme/api", active=False)

    rows = client.get("/api/admin/installations", headers=auth(admin)).json()

    assert len(rows) == 2
    assert {r["name"] for r in rows} == {"acme/api"}
    assert {r["user"] for r in rows} == {"@boss", "@regular"}
    assert {r["active"] for r in rows} == {True, False}


def test_admin_user_detail_returns_counts_and_the_rows_behind_them(client, db_session):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)
    other = make_user(db_session, 2, "regular")

    installation = make_installation(db_session, other, "acme/web")
    make_review(db_session, installation, 11, 65, "changes_requested")
    make_comment_target = make_review(db_session, installation, 12, 95, "approved")
    db_session.add(ReviewComment(
        review_id=make_comment_target.id,
        file_path="app.py",
        line=3,
        type="security",
        severity="critical",
        message="Hardcoded secret.",
        suggestion=None,
    ))
    db_session.commit()

    detail = client.get(f"/api/admin/users/{other.id}", headers=auth(admin)).json()

    assert detail["handle"] == "@regular"
    # `repos` / `reviews` stay counts here, as they are in the list — the rows live
    # under their own keys rather than shadowing them with a different type.
    assert detail["repos"] == 1
    assert detail["reviews"] == 2
    assert [r["name"] for r in detail["installations"]] == ["acme/web"]
    assert {r["number"] for r in detail["recentReviews"]} == {11, 12}


def test_admin_user_detail_404s_on_an_unknown_user(client, db_session):
    admin = make_user(db_session, 1, "boss", role=ROLE_ADMIN)

    resp = client.get("/api/admin/users/999", headers=auth(admin))

    assert resp.status_code == 404
