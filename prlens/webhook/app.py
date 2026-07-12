import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal, NamedTuple

import httpx
import jwt as pyjwt
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from auth.github_oauth import (
    OAuthError,
    exchange_code_for_token,
    get_github_auth_url,
    get_github_user,
)
from database.connection import get_db, init_db
from database.models import Installation, Review, ReviewComment, User
from prlens.config.settings import Settings, SupportedLanguages, load_settings
from prlens.core.agent import Agent
from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient
from prlens.models.pr import PR
from prlens.models.review import ReviewResult, ReviewType, Severity

load_dotenv()

logger = logging.getLogger(__name__)

# Origin the React dashboard is served from. Drives both the CORS allow-list and
# the post-OAuth redirect, so a deployment only has to set this in one place.
FRONTEND_URLS = os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
FRONTEND_ORIGIN = FRONTEND_URLS[0]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"Warning: database init failed: {e}. App will start anyway.")
    yield

app = FastAPI(lifespan=lifespan)

# Auth is a bearer JWT in the Authorization header, not a cookie, so the backend
# (railway.app) and dashboard (ismailmechkene.dev) can live on different domains.
# The signing key is shared with the OAuth callback that mints the token below.
#
# Falling back to a *published* constant would let anyone forge a token for any
# user id on a deployment that forgot to set SESSION_SECRET, so an unset secret
# falls back to a random per-process one instead: tokens then simply do not
# survive a restart, which is a login prompt rather than a takeover.
JWT_SECRET = os.getenv("SESSION_SECRET")
if not JWT_SECRET:
    logger.warning(
        "SESSION_SECRET is not set; using a random per-process signing key. "
        "Sessions will not survive a restart and will not work across replicas."
    )
    JWT_SECRET = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_TTL = timedelta(days=30)

# The dashboard authenticates with a bearer token, so no credentialed cookies
# cross the origin boundary. allow_credentials stays False and the Authorization
# header is allowed through for the preflight.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_processing_lock = threading.Lock()
_processing_prs: set = set()
_last_processed: dict = {}
DEBOUNCE_SECONDS = 30

# Installation.languages stores the enabled SupportedLanguages values; the
# dashboard renders every language in this map, in this order.
LANGUAGE_DISPLAY_NAMES: dict[SupportedLanguages, str] = {
    SupportedLanguages.PYTHON: "Python",
    SupportedLanguages.JAVASCRIPT: "JavaScript",
    SupportedLanguages.TYPESCRIPT: "TypeScript",
    SupportedLanguages.JAVA: "Java",
}

# ReviewType.DOCUMENTATION has no slice in the dashboard's issue donut.
ISSUE_CATEGORIES: dict[ReviewType, str] = {
    ReviewType.SECURITY: "Security",
    ReviewType.QUALITY: "Quality",
    ReviewType.PERFORMANCE: "Performance",
    ReviewType.STYLE: "Style",
}

SCORE_TREND_DAYS = 30


class ReviewerMapEntry(BaseModel):
    key: str
    value: str


class RepoSettingsPayload(BaseModel):
    minSeverity: Severity
    languages: dict[str, bool]
    approveThreshold: int = Field(ge=0, le=100)
    changesThreshold: int = Field(ge=0, le=100)
    excluded: list[str]
    reviewerMap: list[ReviewerMapEntry]


class ActivePayload(BaseModel):
    active: bool


class EnableRepoPayload(BaseModel):
    owner: str
    visibility: Literal["Public", "Private"] = "Public"

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _target_languages(values: list | None, repo_name: str) -> list[SupportedLanguages]:
    """Installation.languages -> enum members, dropping anything unrecognised."""
    languages = []
    for value in values or []:
        try:
            languages.append(SupportedLanguages(value))
        except ValueError:
            logger.warning("%s: ignoring unknown target language %r", repo_name, value)
    return languages


def _reviewers_mapping(raw: dict | None, repo_name: str) -> dict[ReviewType, str]:
    """Installation.reviewer_map -> {ReviewType: reviewer}.

    The keys are free-form strings on the settings endpoint, so a typo must be
    dropped rather than blow up the review.
    """
    mapping = {}
    for key, reviewer in (raw or {}).items():
        try:
            mapping[ReviewType(key)] = reviewer
        except ValueError:
            logger.warning("%s: ignoring reviewer mapping for unknown review type %r", repo_name, key)
    return mapping


def _settings_from_installation(installation: Installation, defaults: Settings) -> Settings:
    """Build the agent's Settings from a repo's dashboard configuration.

    Two fields are not configurable per repo: ``llm_model`` comes from the file
    settings, and ``max_workers`` keeps the model default. ``large_pr_threshold``
    is likewise not stored, so it is inherited from the file settings rather than
    being silently reset when a repo is connected.
    """
    return Settings(
        llm_model=defaults.llm_model,
        large_pr_threshold=defaults.large_pr_threshold,
        min_severity=installation.min_severity,
        target_languages=_target_languages(installation.languages, installation.repo_name),
        excluded_files=list(installation.excluded_files or []),
        reviewers_mapping=_reviewers_mapping(installation.reviewer_map, installation.repo_name),
        approve_threshold=installation.approve_threshold,
        changes_threshold=installation.changes_threshold,
    )


class _RepoConfig(NamedTuple):
    settings: Settings
    active: bool


def _repo_config(repo_name: str) -> _RepoConfig | None:
    """The repo's dashboard configuration, or None to fall back to file settings.

    Returns None when there is no database configured, no installation row for the
    repo, or the lookup fails. A database problem must not stop a review, so the
    caller degrades to ``load_settings()`` instead of raising.

    Runs on the background-task thread, so it owns its engine and session — see
    ``_persist_review`` for the same reasoning.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    try:
        engine = create_engine(db_url)
        local_session = sessionmaker(bind=engine)
        db = local_session()
        try:
            installations = db.query(Installation).filter(
                Installation.repo_name == repo_name
            ).order_by(Installation.id).all()

            if not installations:
                return None

            # The unique key is (user_id, repo_name), so the same repo can be
            # connected by several users. Reviewing stays on as long as one of them
            # has it enabled, and that installation's settings are the ones used —
            # taking an arbitrary .first() would let one paused installation
            # silently disable reviewing for everybody else on the repo.
            active = next((inst for inst in installations if inst.active), None)
            chosen = active if active is not None else installations[0]

            return _RepoConfig(
                _settings_from_installation(chosen, load_settings()),
                active is not None,
            )
        finally:
            db.close()
            engine.dispose()
    except Exception:
        logger.exception("Could not load settings for %s; using file settings", repo_name)
        return None


def _outcome_to_status(result: ReviewResult, publisher: PRPublisher) -> str:
    """The value stored in ``Review.status`` for a finished review.

    Takes the publisher because the approve/changes thresholds live on it, so the
    stored status is guaranteed to be the same verdict that was posted to GitHub.
    """
    return publisher.determine_outcome(result).value


def _persist_review(repo_name: str, pr: PR, result: ReviewResult, status: str) -> None:
    """Store a completed review and its comments.

    Background tasks run on a worker thread, so the request-scoped session from
    ``get_db`` cannot be used here. Build a short-lived engine + session owned by
    this thread and dispose of both before returning.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL unset; not storing review for %s", repo_name)
        return

    engine = create_engine(db_url)
    local_session = sessionmaker(bind=engine)
    db = local_session()
    try:
        installations = db.query(Installation).filter(
            Installation.repo_name == repo_name,
            Installation.active.is_(True),
        ).all()

        if not installations:
            logger.info("No active installation for %s; review not stored", repo_name)
            return

        # Review.pr_title is a VARCHAR(255) while GitHub allows titles up to 256
        # characters, and an over-long value is a hard error on Postgres (not a
        # silent truncation), which would lose the whole row.
        pr_title = (pr.title or "")[:255]

        # One repo can be connected by several users — the unique key is
        # (user_id, repo_name) — and each has their own dashboard, so the review is
        # mirrored onto every active installation rather than an arbitrary one.
        for installation in installations:
            review = Review(
                installation_id=installation.id,
                pr_number=pr.number,
                pr_title=pr_title,
                score=result.score,
                status=status,
            )
            db.add(review)
            db.flush()  # assigns review.id for the comment rows below

            for comment in result.comments:
                db.add(ReviewComment(
                    review_id=review.id,
                    file_path=comment.file_path,
                    # line is NOT NULL; file-level comments carry no line number.
                    line=comment.line or 0,
                    type=comment.type.value,
                    severity=comment.severity.value,
                    message=comment.message,
                    suggestion=comment.suggestion,
                ))

        db.commit()
    finally:
        db.close()
        engine.dispose()


def run_agent(repo_name: str, pr_number: int, actor: str) -> None:
    pr_key = f"{repo_name}#{pr_number}"
    now = time.time()

    with _processing_lock:
        # Reject if already running
        if pr_key in _processing_prs:
            print(f"Skipping: {pr_key} already processing")
            return

        # Reject if processed too recently
        last = _last_processed.get(pr_key, 0)
        if now - last < DEBOUNCE_SECONDS:
            print(f"Debouncing: {pr_key} processed {now - last:.1f}s ago")
            return

        # Mark as active
        _processing_prs.add(pr_key)
        _last_processed[pr_key] = now

        # Timestamps older than the debounce window can no longer suppress
        # anything, so drop them instead of keeping one entry per PR ever seen
        # for the lifetime of the process.
        for key, last_seen in list(_last_processed.items()):
            if key != pr_key and now - last_seen >= DEBOUNCE_SECONDS:
                del _last_processed[key]

    try:
        # A connected repo reviews with the settings edited in the dashboard;
        # anything else falls back to .aireviewer.yml.
        config = _repo_config(repo_name)

        if config is not None and not config.active:
            print(f"Paused: reviewing is disabled for {repo_name}")
            return

        settings = config.settings if config is not None else load_settings()
        github_client = GitHubClient()
        llm_client = LLMClient(settings.llm_model)
        pr_fetcher = PRFetcher(github_client)
        analyzer = Analyzer(llm_client)
        pr_publisher = PRPublisher(github_client, settings)
        agent = Agent(llm_client, pr_fetcher, pr_publisher, analyzer, settings)

        # Runs on a BackgroundTasks worker after the webhook response has already
        # been sent, so an escaping exception cannot be turned into an HTTP error —
        # it would only surface as an unhandled ASGI error. Log it and stop.
        try:
            review_output = agent.run(repo_name, pr_number, actor)
        except Exception:
            logger.exception("Review failed for %s", pr_key)
            return

        # The review is already live on the PR by now, so nothing below may be
        # allowed to fail the task — the dashboard row is a best-effort mirror.
        try:
            pr, result = review_output
            _persist_review(repo_name, pr, result, _outcome_to_status(result, pr_publisher))
        except Exception:
            logger.exception("Could not store review for %s", pr_key)
    finally:
        with _processing_lock:
            _processing_prs.discard(pr_key)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.removeprefix("Bearer ")
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload["user_id"]
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except KeyError:
        # Correctly signed but not one of ours (no user_id claim): still a failed
        # authentication, not a 500.
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    else:
        return f"{seconds // 86400}d ago"


def get_installation(db: Session, user: User, repo_name: str) -> Installation:
    installation = db.query(Installation).filter(
        Installation.user_id == user.id,
        Installation.repo_name == repo_name,
    ).first()
    if not installation:
        raise HTTPException(status_code=404, detail=f"Repo '{repo_name}' not found")
    return installation


def serialize_repo(installation: Installation) -> dict:
    return {
        "name": installation.repo_name,
        "owner": installation.owner,
        "visibility": installation.visibility,
        "updated": time_ago(installation.installed_at),
        "connected": installation.connected,
        "active": installation.active,
    }


def serialize_settings(installation: Installation) -> dict:
    enabled = set(installation.languages or [])
    return {
        "minSeverity": installation.min_severity,
        "languages": {
            display: language.value in enabled
            for language, display in LANGUAGE_DISPLAY_NAMES.items()
        },
        "approveThreshold": installation.approve_threshold,
        "changesThreshold": installation.changes_threshold,
        "excluded": installation.excluded_files or [],
        "reviewerMap": [
            {"key": key, "value": value}
            for key, value in (installation.reviewer_map or {}).items()
        ],
    }


def serialize_review(review: Review) -> dict:
    return {
        "repo": review.installation.repo_name,
        "number": review.pr_number,
        "title": review.pr_title,
        "score": review.score,
        "status": review.status,
        "reviewedAt": time_ago(review.reviewed_at),
    }


def issue_breakdown(db: Session, installation: Installation) -> list[dict]:
    counts = dict(
        db.query(ReviewComment.type, func.count(ReviewComment.id))
        .join(Review, ReviewComment.review_id == Review.id)
        .filter(Review.installation_id == installation.id)
        .group_by(ReviewComment.type)
        .all()
    )
    return [
        {"category": category, "value": counts.get(review_type.value, 0)}
        for review_type, category in ISSUE_CATEGORIES.items()
    ]


def score_trend(db: Session, installation: Installation) -> list[int]:
    """Daily average scores over the trailing window, oldest first."""
    # Review.reviewed_at is a naive UTC column, so compare against a naive bound.
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=SCORE_TREND_DAYS
    )
    rows = db.query(Review.reviewed_at, Review.score).filter(
        Review.installation_id == installation.id,
        Review.reviewed_at >= cutoff,
    ).all()

    # Grouped in Python rather than SQL: CAST(... AS DATE) is not portable to SQLite.
    daily: dict = defaultdict(list)
    for reviewed_at, score in rows:
        daily[reviewed_at.date()].append(score)

    return [round(sum(scores) / len(scores)) for _, scores in sorted(daily.items())]


@app.get("/")
def health_check():
    return {"status": "ok", "service": "PRLens"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature, secret):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)
    event_type = request.headers.get("X-GitHub-Event", "")

    if event_type != "pull_request":
        return {"status": "ignored", "reason": "not a pull_request event"}

    action = payload.get("action", "")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"action '{action}' not handled"}

    repo_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    actor = payload["pull_request"]["user"]["login"]

    background_tasks.add_task(run_agent, repo_name, pr_number, actor)
    return {"status": "accepted"}


@app.get("/auth/github")
def github_login():
    return RedirectResponse(get_github_auth_url())


@app.get("/auth/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
    # An expired or already-redeemed code (a reload of this URL, or the back
    # button) comes back from GitHub as HTTP 200 with an error body and no
    # access_token. That is a bad request, not a crash.
    try:
        token = await exchange_code_for_token(code)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"GitHub sign-in failed: {e}")

    github_user = await get_github_user(token)
    if not isinstance(github_user, dict) or "id" not in github_user or "login" not in github_user:
        raise HTTPException(status_code=400, detail="Could not read the GitHub profile")

    # Save or update user in database
    user = db.query(User).filter(User.github_id == github_user["id"]).first()
    if not user:
        user = User(
            github_id=github_user["id"],
            name=github_user.get("name") or github_user["login"],
            handle=f"@{github_user['login']}",
            initials=github_user["login"][:2].upper(),
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)

    user.github_token = token
    db.commit()
    db.refresh(user)

    # Cross-domain auth: mint a bearer JWT and hand it to the dashboard in the URL.
    # The dashboard (served by Vite, not this app) stores it and sends it back as
    # an Authorization header on every API call — see get_current_user.
    session_token = pyjwt.encode(
        {"user_id": user.id, "exp": datetime.now(timezone.utc) + JWT_TTL},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return RedirectResponse(f"{FRONTEND_ORIGIN}/dashboard?token={session_token}")


@app.get("/api/user")
def get_user(current_user: User = Depends(get_current_user)):
    return {
        "name": current_user.name,
        "handle": current_user.handle,
        "initials": current_user.initials,
        "avatarUrl": current_user.avatar_url,
    }


@app.get("/api/repos")
def get_repos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installations = db.query(Installation).filter(
        Installation.user_id == current_user.id
    ).all()

    return [serialize_repo(inst) for inst in installations]


@app.get("/api/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_repos = db.query(Installation).filter(
        Installation.user_id == current_user.id
    ).count()

    total_prs = db.query(Review).join(Installation).filter(
        Installation.user_id == current_user.id
    ).count()

    total_issues = db.query(ReviewComment).join(Review).join(Installation).filter(
        Installation.user_id == current_user.id
    ).count()

    return {
        "stats": [
            {
                "id": "repos",
                "label": "Repos connected",
                "value": str(total_repos),
                "delta": "",
                "trend": "neutral",
                "icon": "git-branch",
                "iconColor": "var(--pa)"
            },
            {
                "id": "prs",
                "label": "PRs reviewed",
                "value": str(total_prs),
                "delta": "",
                "trend": "neutral",
                "icon": "git-pull-request",
                "iconColor": "var(--pa)"
            },
            {
                "id": "issues",
                "label": "Issues caught",
                "value": str(total_issues),
                "delta": "",
                "trend": "neutral",
                "icon": "shield-alert",
                "iconColor": "var(--pa)"
            },
        ]
    }

@app.get("/api/reviews")
def get_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    reviews = db.query(Review).options(
        joinedload(Review.installation)
    ).join(Installation).filter(
        Installation.user_id == current_user.id
    ).order_by(Review.reviewed_at.desc()).limit(limit).all()

    return [serialize_review(r) for r in reviews]


# NOTE: a repo `name` is a GitHub full_name ("acme/api-gateway"), so every route
# below uses the `:path` converter — the default one stops at a slash. For the
# same reason the bare "/api/repos/{name:path}" route is registered *last*: a
# greedy path converter registered first would swallow the "/reviews",
# "/settings", "/active" and "/enable" suffixes into `name`.


@app.get("/api/repos/{name:path}/reviews")
def get_repo_reviews(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    installation = get_installation(db, current_user, name)

    reviews = db.query(Review).options(
        joinedload(Review.installation)
    ).filter(
        Review.installation_id == installation.id
    ).order_by(Review.reviewed_at.desc()).all()

    return [serialize_review(r) for r in reviews]


@app.put("/api/repos/{name:path}/settings")
def update_repo_settings(
    name: str,
    settings: RepoSettingsPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    installation = get_installation(db, current_user, name)

    installation.min_severity = settings.minSeverity.value
    installation.languages = [
        language.value
        for language, display in LANGUAGE_DISPLAY_NAMES.items()
        if settings.languages.get(display, False)
    ]
    installation.approve_threshold = settings.approveThreshold
    installation.changes_threshold = settings.changesThreshold
    installation.excluded_files = settings.excluded
    installation.reviewer_map = {e.key: e.value for e in settings.reviewerMap}

    db.commit()
    db.refresh(installation)

    return serialize_settings(installation)


@app.put("/api/repos/{name:path}/active")
def set_repo_active(
    name: str,
    payload: ActivePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    installation = get_installation(db, current_user, name)

    installation.active = payload.active
    db.commit()

    return {"active": installation.active}


@app.post("/api/repos/{name:path}/enable")
def enable_repo(
    name: str,
    payload: EnableRepoPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    installation = db.query(Installation).filter(
        Installation.user_id == current_user.id,
        Installation.repo_name == name,
    ).first()

    if not installation:
        # New installations inherit the agent's own defaults.
        defaults = Settings()
        installation = Installation(
            user_id=current_user.id,
            repo_name=name,
            owner=payload.owner,
            visibility=payload.visibility,
            connected=True,
            active=True,
            min_severity=defaults.min_severity.value,
            languages=[language.value for language in SupportedLanguages],
            approve_threshold=defaults.approve_threshold,
            changes_threshold=defaults.changes_threshold,
            excluded_files=[],
            reviewer_map={},
        )
        db.add(installation)
        try:
            db.commit()
        except IntegrityError:
            # Two enables raced for the same repo: both saw no row, both inserted,
            # and the (user_id, repo_name) unique key rejected the loser. Reuse the
            # row the winner committed instead of returning a 500 — the endpoint is
            # meant to be idempotent.
            db.rollback()
            installation = db.query(Installation).filter(
                Installation.user_id == current_user.id,
                Installation.repo_name == name,
            ).first()
            if installation is None:
                raise HTTPException(status_code=500, detail="Could not enable repo")
            installation.connected = True
            installation.active = True
            db.commit()
    else:
        installation.connected = True
        installation.active = True
        db.commit()

    db.refresh(installation)

    return serialize_repo(installation)


@app.get("/api/github/repos")
async def get_github_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.github_token:
        raise HTTPException(status_code=401, detail="No GitHub token stored")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={
                "Authorization": f"Bearer {current_user.github_token}",
                "Accept": "application/json",
            }
        )

    # An error body is a dict, not a list, and the comprehension below would just
    # skip it — the dashboard would show "no repositories" for what is really a
    # revoked or expired OAuth token. Surface it instead.
    if response.status_code != 200:
        logger.warning("GitHub /user/repos returned %s", response.status_code)
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub token expired")
        raise HTTPException(status_code=502, detail="Could not list repositories from GitHub")

    github_repos = response.json()

    connected_names = {
        inst.repo_name
        for inst in db.query(Installation).filter(
            Installation.user_id == current_user.id
        ).all()
    }

    return [
        {
            "name": r["full_name"],
            "owner": r["owner"]["login"],
            "visibility": "Private" if r["private"] else "Public",
            "updated": time_ago(datetime.fromisoformat(
                r["updated_at"].replace("Z", "+00:00")
            )),
            "connected": r["full_name"] in connected_names,
        }
        for r in github_repos
        if isinstance(r, dict)  # guard against error responses
    ]


# Registered last on purpose: its greedy `:path` name would otherwise capture the
# "/reviews", "/settings", "/active" and "/enable" suffixes of the routes above.
@app.get("/api/repos/{name:path}")
def get_repo(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    installation = get_installation(db, current_user, name)

    latest = db.query(Review).filter(
        Review.installation_id == installation.id
    ).order_by(Review.reviewed_at.desc()).first()

    trend = score_trend(db, installation)
    current_score = latest.score if latest else 0

    return {
        **serialize_repo(installation),
        "description": installation.description or "",
        "scoreTrend": trend,
        "currentScore": current_score,
        "scoreDelta": current_score - trend[0] if trend else 0,
        "issues": issue_breakdown(db, installation),
        "settings": serialize_settings(installation),
    }