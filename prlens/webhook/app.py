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
from database.models import ROLE_ADMIN, Installation, Review, ReviewComment, User
from prlens.config.settings import Settings, SupportedLanguages, load_settings
from prlens.core.agent import Agent
from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher, ReviewOutcome
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient
from prlens.models.pr import PR
from prlens.models.review import ReviewResult, ReviewType, Severity

load_dotenv()

# uvicorn configures its own loggers, not the root one, so without this the app's
# own INFO records have no handler and are dropped — which is how a review that
# never ran left no trace in the deployment logs. No-op if logging is already set up.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

# Origin the React dashboard is served from. Drives both the CORS allow-list and
# the post-OAuth redirect, so a deployment only has to set this in one place.
FRONTEND_URLS = os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
FRONTEND_ORIGIN = FRONTEND_URLS[0]


def _check_github_credentials() -> None:
    """Fail loudly at boot if the GitHub App credentials cannot be used.

    Building the client is the step that reads the App's private key and exchanges
    it for an installation token. Doing it once at startup turns "pull requests are
    silently never reviewed" into a single, obvious line in the deployment log.
    """
    try:
        GitHubClient()
    except Exception:
        logger.exception(
            "GitHub credentials are unusable — PULL REQUESTS WILL NOT BE REVIEWED. "
            "Check GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID and the private key "
            "(GITHUB_APP_PRIVATE_KEY_B64 in a container: the .pem file is not in the image)."
        )
    else:
        logger.info("GitHub App credentials OK")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
    except Exception:
        logger.exception("Database init failed. App will start anyway.")

    _check_github_credentials()
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

# Review.status values that mean the review did not complete cleanly. Tracked as a
# single tile on the admin dashboard: a cluster of these across unrelated repos is
# what an Azure OpenAI outage looks like from the inside.
FAILED_STATUSES = (ReviewOutcome.INCOMPLETE.value, ReviewOutcome.TOTAL_FAILURE.value)

# Page size for the admin lists. They are bounded because they are the only views
# in the app whose result set grows with the *whole* deployment rather than with
# one user's repos.
ADMIN_PAGE_LIMIT = 100

# GitHub caps per_page at 100, so the Connect page walks pages. The page limit is
# only a runaway guard — 20 pages is 2000 repos.
GITHUB_REPOS_PER_PAGE = 100
GITHUB_REPO_PAGE_LIMIT = 20

# The GitHub App PRLens is installed as. Used to detach a repo from the app when it
# is disconnected; without it, a disconnect can only clear the dashboard's own rows.
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")

# Ordering for "which severity is stricter", used when several installations of the
# same repo have to be reconciled into one configuration (see _merge_settings).
SEVERITY_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
    Severity.CRITICAL: 3,
}

# Background tasks run on a worker thread, so they cannot use the request-scoped
# session from ``get_db``. They share this lazily-built engine instead of each
# building a throwaway one: an engine owns a connection pool, and creating and
# disposing a pool per webhook event means a fresh TCP + TLS handshake to Postgres
# every time. ``pool_pre_ping`` covers connections the database dropped while the
# pool sat idle between events.
_engine_lock = threading.Lock()
_background_engine = None
_background_engine_url: str | None = None
_background_sessionmaker: sessionmaker | None = None


def _background_session_factory() -> sessionmaker | None:
    """Session factory for background threads, or None when there is no database."""
    global _background_engine, _background_engine_url, _background_sessionmaker

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    with _engine_lock:
        # Rebuilt if DATABASE_URL changes, which in practice only happens in tests.
        if _background_sessionmaker is None or _background_engine_url != db_url:
            if _background_engine is not None:
                _background_engine.dispose()
            _background_engine = create_engine(db_url, pool_pre_ping=True)
            _background_sessionmaker = sessionmaker(bind=_background_engine)
            _background_engine_url = db_url
        return _background_sessionmaker


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


def _merge_settings(installations: list[Installation], defaults: Settings) -> Settings:
    """Reconcile several installations of one repo into the settings to review with.

    The unique key is (user_id, repo_name), so the same repo can be connected by
    more than one user — but only one review is posted to the pull request, so the
    configurations have to become one. Every field resolves towards the *strictest*
    option, which is the only rule under which no user's settings can be silently
    weakened by somebody else's:

    * ``min_severity`` — the lowest, so a comment anyone wants to see survives.
    * ``target_languages`` — the union. An empty list means "no language filter",
      i.e. review everything, so it is the strictest value and absorbs the rest.
    * ``excluded_files`` — the intersection: a file is only skipped if *everyone*
      skips it.
    * ``approve_threshold`` / ``changes_threshold`` — the highest, so the repo is
      the hardest to approve and the quickest to have changes requested.
    * ``reviewers_mapping`` — merged; the earliest installation wins a review type
      that two of them map to different reviewers.
    """
    configs = [_settings_from_installation(inst, defaults) for inst in installations]

    languages: list[SupportedLanguages] = []
    if all(config.target_languages for config in configs):
        for config in configs:
            for language in config.target_languages:
                if language not in languages:
                    languages.append(language)

    excluded = [
        pattern
        for pattern in configs[0].excluded_files
        if all(pattern in config.excluded_files for config in configs[1:])
    ]

    reviewers: dict[ReviewType, str] = {}
    for config in reversed(configs):  # earliest installation applied last, so it wins
        reviewers.update(config.reviewers_mapping)

    return Settings(
        llm_model=defaults.llm_model,
        large_pr_threshold=defaults.large_pr_threshold,
        min_severity=min(
            (config.min_severity for config in configs),
            key=lambda severity: SEVERITY_RANK[severity],
        ),
        target_languages=languages,
        excluded_files=excluded,
        reviewers_mapping=reviewers,
        approve_threshold=max(config.approve_threshold for config in configs),
        changes_threshold=max(config.changes_threshold for config in configs),
    )


class _RepoConfig(NamedTuple):
    settings: Settings
    active: bool


def _repo_config(repo_name: str) -> _RepoConfig | None:
    """The repo's dashboard configuration, or None to fall back to file settings.

    Returns None when there is no database configured, no installation row for the
    repo, or the lookup fails. A database problem must not stop a review, so the
    caller degrades to ``load_settings()`` instead of raising.
    """
    session_factory = _background_session_factory()
    if session_factory is None:
        return None

    try:
        db = session_factory()
        try:
            installations = db.query(Installation).filter(
                Installation.repo_name == repo_name
            ).order_by(Installation.id).all()

            if not installations:
                return None

            # Reviewing stays on as long as one user has it enabled: an arbitrary
            # .first() would let a single paused installation silently disable
            # reviewing for everybody else on the repo.
            active = [inst for inst in installations if inst.active]
            if not active:
                return _RepoConfig(
                    _settings_from_installation(installations[0], load_settings()),
                    False,
                )

            return _RepoConfig(_merge_settings(active, load_settings()), True)
        finally:
            db.close()
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
    ``get_db`` cannot be used here — see ``_background_session_factory``.
    """
    session_factory = _background_session_factory()
    if session_factory is None:
        logger.warning("DATABASE_URL unset; not storing review for %s", repo_name)
        return

    db = session_factory()
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


def run_agent(repo_name: str, pr_number: int, actor: str) -> None:
    pr_key = f"{repo_name}#{pr_number}"
    now = time.time()

    with _processing_lock:
        # Reject if already running
        if pr_key in _processing_prs:
            logger.info("Skipping %s: already processing", pr_key)
            return

        # Reject if processed too recently
        last = _last_processed.get(pr_key, 0)
        if now - last < DEBOUNCE_SECONDS:
            logger.info("Debouncing %s: processed %.1fs ago", pr_key, now - last)
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

    # This whole body runs on a BackgroundTasks worker, *after* the webhook has
    # answered 200. Nothing raised here can become an HTTP error any more — it only
    # surfaces as an unhandled ASGI traceback — so every failure is caught and
    # logged. Building the clients is inside the guard as much as the review is:
    # GitHubClient() raises when the App credentials are unusable, and that used to
    # escape silently, which looked exactly like "the agent never runs".
    try:
        logger.info("Reviewing %s (opened by %s)", pr_key, actor)

        # A connected repo reviews with the settings edited in the dashboard;
        # anything else falls back to .aireviewer.yml.
        config = _repo_config(repo_name)

        if config is not None and not config.active:
            logger.info("Paused: reviewing is disabled for %s", repo_name)
            return

        settings = config.settings if config is not None else load_settings()
        github_client = GitHubClient()
        llm_client = LLMClient(settings.llm_model)
        pr_fetcher = PRFetcher(github_client)
        analyzer = Analyzer(llm_client)
        pr_publisher = PRPublisher(github_client, settings)
        agent = Agent(llm_client, pr_fetcher, pr_publisher, analyzer, settings)

        pr, result = agent.run(repo_name, pr_number, actor)
        logger.info("Reviewed %s: score %s", pr_key, result.score)

        # The review is already live on the PR by now, so nothing below may be
        # allowed to fail the task — the dashboard row is a best-effort mirror.
        try:
            _persist_review(repo_name, pr, result, _outcome_to_status(result, pr_publisher))
        except Exception:
            logger.exception("Could not store review for %s", pr_key)
    except Exception:
        logger.exception("Review failed for %s", pr_key)
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


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Gate for /api/admin: authenticated *and* an administrator.

    The role is read from the database row on every request (get_current_user
    loads it), not from a claim in the JWT — a token minted while the user was an
    admin therefore stops opening these routes the moment the role is revoked,
    rather than at the end of its 30-day life.
    """
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return current_user


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

    # Save or update user in database. github_id is the identity — a login can be
    # renamed, and the new owner of the old login is a different person — so the
    # profile fields are refreshed on every sign-in rather than frozen at the
    # values captured the first time the user appeared.
    login = github_user["login"]
    user = db.query(User).filter(User.github_id == github_user["id"]).first()
    if not user:
        user = User(github_id=github_user["id"])
        db.add(user)

    user.name = github_user.get("name") or login
    user.handle = f"@{login}"
    user.initials = login[:2].upper()
    user.avatar_url = github_user.get("avatar_url")
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
        # Drives whether the dashboard offers the admin section. It is a hint for
        # the UI only: every /api/admin route re-checks the role server-side.
        "role": current_user.role,
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

    active_repos = db.query(Installation).filter(
        Installation.user_id == current_user.id,
        Installation.active.is_(True),
    ).count()

    # The dashboard has a tile for this, and the endpoint never sent it — so it sat
    # empty. None (no reviews yet) is an em dash rather than a misleading 0.
    average_score = db.query(func.avg(Review.score)).join(Installation).filter(
        Installation.user_id == current_user.id
    ).scalar()
    average_score_text = str(round(average_score)) if average_score is not None else "—"

    reviews_this_week = db.query(Review).join(Installation).filter(
        Installation.user_id == current_user.id,
        Review.reviewed_at >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7),
    ).count()

    return {
        "stats": [
            {
                "id": "prs",
                "label": "PRs reviewed",
                "value": str(total_prs),
                "delta": f"+{reviews_this_week} this wk" if reviews_this_week else "",
                "trend": "up" if reviews_this_week else "neutral",
                "icon": "git-pull-request",
                "iconColor": "var(--pa)"
            },
            {
                "id": "score",
                "label": "Average score",
                "value": average_score_text,
                "delta": "",
                "trend": "neutral",
                "icon": "gauge",
                "iconColor": "var(--success)"
            },
            {
                "id": "issues",
                "label": "Issues caught",
                "value": str(total_issues),
                "delta": "",
                "trend": "neutral",
                "icon": "shield-alert",
                "iconColor": "var(--danger)"
            },
            {
                "id": "repos",
                "label": "Repos connected",
                "value": str(total_repos),
                "delta": f"{active_repos} active" if total_repos else "",
                "trend": "neutral",
                "icon": "git-branch",
                "iconColor": "var(--done)"
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

    github_repos: list = []
    async with httpx.AsyncClient() as client:
        # /user/repos is paginated: one page of 100 silently hid every repo beyond
        # the hundredth from users with more than that. Walk pages until GitHub
        # returns a short one; GITHUB_REPO_PAGE_LIMIT is a stop so a bad response
        # cannot spin here forever.
        for page in range(1, GITHUB_REPO_PAGE_LIMIT + 1):
            response = await client.get(
                "https://api.github.com/user/repos",
                params={
                    "per_page": GITHUB_REPOS_PER_PAGE,
                    "page": page,
                    "sort": "updated",
                },
                headers={
                    "Authorization": f"Bearer {current_user.github_token}",
                    "Accept": "application/json",
                },
            )

            # An error body is a dict, not a list, and the comprehension below would
            # just skip it — the dashboard would show "no repositories" for what is
            # really a revoked or expired OAuth token. Surface it instead.
            if response.status_code != 200:
                logger.warning("GitHub /user/repos returned %s", response.status_code)
                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail="GitHub token expired")
                raise HTTPException(
                    status_code=502,
                    detail="Could not list repositories from GitHub",
                )

            batch = response.json()
            if not isinstance(batch, list):
                raise HTTPException(
                    status_code=502,
                    detail="Unexpected response from GitHub",
                )

            github_repos.extend(batch)
            if len(batch) < GITHUB_REPOS_PER_PAGE:
                break  # short page: that was the last one
        else:
            logger.warning(
                "Stopped listing repos for %s at the %s-page limit",
                current_user.handle,
                GITHUB_REPO_PAGE_LIMIT,
            )

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


async def _detach_repo_from_github_app(repo_name: str, token: str | None) -> bool:
    """Remove one repo from this GitHub App's installation. Best effort.

    Deleting the Installation row stops the dashboard from showing the repo, but
    GitHub keeps delivering webhooks for it — and a delivery for a repo PRLens has
    no row for still gets reviewed, with the file settings. So "disconnect" only
    really disconnects if the repo is detached on GitHub's side too.

    Returns whether GitHub confirmed the removal. A failure here must not fail the
    disconnect: the row still goes, and the caller reports what did not happen.
    """
    if not token or not GITHUB_APP_ID:
        return False

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    try:
        async with httpx.AsyncClient() as client:
            repo = await client.get(
                f"https://api.github.com/repos/{repo_name}", headers=headers
            )
            if repo.status_code != 200:
                return False
            repo_id = repo.json().get("id")

            installations = await client.get(
                "https://api.github.com/user/installations", headers=headers
            )
            if installations.status_code != 200:
                return False

            ours = next(
                (
                    inst
                    for inst in installations.json().get("installations", [])
                    if str(inst.get("app_id")) == str(GITHUB_APP_ID)
                ),
                None,
            )
            if ours is None or repo_id is None:
                return False

            removed = await client.delete(
                f"https://api.github.com/user/installations/{ours['id']}/repositories/{repo_id}",
                headers=headers,
            )
            return removed.status_code == 204
    except Exception:
        logger.exception("Could not detach %s from the GitHub App installation", repo_name)
        return False


@app.delete("/api/repos/{name:path}")
async def disconnect_repo(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove PRLens from a repo: its installation, settings and review history.

    The GitHub side is detached first — if that is going to fail, it fails while the
    row is still there, and the caller is told. The row itself is then deleted, and
    the ``cascade`` on Installation.reviews takes the reviews and their comments
    with it.
    """
    installation = get_installation(db, current_user, name)

    github_removed = await _detach_repo_from_github_app(name, current_user.github_token)

    db.delete(installation)
    db.commit()

    return {"name": name, "githubRemoved": github_removed}


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


# ---------------------------------------------------------------------------
# Admin
#
# Every route below is scoped to the whole deployment rather than to the caller,
# and is gated on ``require_admin``. They are all read-only on purpose: an admin
# surface that can also write is a privilege-escalation path, so a role is only
# ever granted out of band (scripts/set_admin.py) and nothing here mutates another
# user's repos, settings or history.
#
# Being an admin adds these views; it takes nothing away. An admin still has their
# own installations and their own /api/* data, so they move between the global view
# and their personal dashboard freely — the two are separate routes, not a mode.
#
# `/api/admin/...` cannot be captured by the greedy `/api/repos/{name:path}` route
# above: that one only matches paths beginning with `/api/repos/`.
# ---------------------------------------------------------------------------


def serialize_admin_user(user: User, repos: int, reviews: int, last: datetime | None) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "handle": user.handle,
        "initials": user.initials,
        "avatarUrl": user.avatar_url,
        "role": user.role,
        "repos": repos,
        "reviews": reviews,
        # No review yet is an em dash rather than a misleading "just now".
        "lastActive": time_ago(last) if last is not None else "—",
    }


def _reviews_per_user(db: Session) -> tuple[dict[int, int], dict[int, datetime]]:
    """(reviews per user_id, most recent review per user_id).

    Aggregated in two grouped queries rather than by walking each user's
    installations, so the users list stays a fixed number of round trips however
    many accounts the deployment has.
    """
    rows = (
        db.query(
            Installation.user_id,
            func.count(Review.id),
            func.max(Review.reviewed_at),
        )
        .join(Review, Review.installation_id == Installation.id)
        .group_by(Installation.user_id)
        .all()
    )
    counts = {user_id: count for user_id, count, _ in rows}
    latest = {user_id: last for user_id, _, last in rows if last is not None}
    return counts, latest


def _repos_per_user(db: Session) -> dict[int, int]:
    return dict(
        db.query(Installation.user_id, func.count(Installation.id))
        .group_by(Installation.user_id)
        .all()
    )


@app.get("/api/admin/stats")
def get_admin_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Deployment-wide tiles. Same shape as /api/stats, so the UI reuses StatCard."""
    total_users = db.query(User).count()
    total_admins = db.query(User).filter(User.role == ROLE_ADMIN).count()

    total_repos = db.query(Installation).count()
    active_repos = db.query(Installation).filter(Installation.active.is_(True)).count()

    total_reviews = db.query(Review).count()
    reviews_this_week = db.query(Review).filter(
        Review.reviewed_at >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7),
    ).count()

    failed_reviews = db.query(Review).filter(Review.status.in_(FAILED_STATUSES)).count()
    failure_rate = round(100 * failed_reviews / total_reviews) if total_reviews else 0

    return {
        "stats": [
            {
                "id": "users",
                "label": "Users",
                "value": str(total_users),
                "delta": f"{total_admins} admin" if total_admins else "",
                "trend": "neutral",
                "icon": "users",
                "iconColor": "var(--pa)",
            },
            {
                "id": "repos",
                "label": "Repos connected",
                "value": str(total_repos),
                "delta": f"{active_repos} active" if total_repos else "",
                "trend": "neutral",
                "icon": "git-branch",
                "iconColor": "var(--done)",
            },
            {
                "id": "reviews",
                "label": "Reviews run",
                "value": str(total_reviews),
                "delta": f"+{reviews_this_week} this wk" if reviews_this_week else "",
                "trend": "up" if reviews_this_week else "neutral",
                "icon": "git-pull-request",
                "iconColor": "var(--success)",
            },
            {
                # A rate that climbs across unrelated repos is the deployment-level
                # signal a per-user dashboard structurally cannot show: it means the
                # LLM backend is failing, not that somebody's code got worse.
                "id": "failures",
                "label": "Failed reviews",
                "value": str(failed_reviews),
                "delta": f"{failure_rate}% of runs" if total_reviews else "",
                "trend": "down" if failed_reviews else "neutral",
                "icon": "shield-alert",
                "iconColor": "var(--danger)",
            },
        ]
    }


@app.get("/api/admin/users")
def get_admin_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = ADMIN_PAGE_LIMIT,
):
    repo_counts = _repos_per_user(db)
    review_counts, last_reviews = _reviews_per_user(db)

    users = db.query(User).order_by(User.id).limit(min(limit, ADMIN_PAGE_LIMIT)).all()

    return [
        serialize_admin_user(
            user,
            repo_counts.get(user.id, 0),
            review_counts.get(user.id, 0),
            last_reviews.get(user.id),
        )
        for user in users
    ]


@app.get("/api/admin/installations")
def get_admin_installations(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = ADMIN_PAGE_LIMIT,
):
    """Every installation across every user.

    The same repo appears once per user who connected it — the unique key is
    (user_id, repo_name) — which is exactly what makes the duplicate-installation
    problem visible here and nowhere else.
    """
    installations = (
        db.query(Installation)
        .options(joinedload(Installation.user))
        .order_by(Installation.installed_at.desc())
        .limit(min(limit, ADMIN_PAGE_LIMIT))
        .all()
    )

    return [
        {
            **serialize_repo(installation),
            "userId": installation.user_id,
            "user": installation.user.handle if installation.user else "—",
        }
        for installation in installations
    ]


@app.get("/api/admin/reviews")
def get_admin_reviews(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 20,
    status: str | None = None,
):
    """The global review feed. ``status=failed`` narrows it to the runs that broke."""
    query = db.query(Review).options(
        joinedload(Review.installation).joinedload(Installation.user)
    ).join(Installation)

    if status == "failed":
        query = query.filter(Review.status.in_(FAILED_STATUSES))
    elif status:
        query = query.filter(Review.status == status)

    reviews = (
        query.order_by(Review.reviewed_at.desc())
        .limit(min(limit, ADMIN_PAGE_LIMIT))
        .all()
    )

    return [
        {
            **serialize_review(review),
            "user": review.installation.user.handle if review.installation.user else "—",
        }
        for review in reviews
    ]


@app.get("/api/admin/users/{user_id}")
def get_admin_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """One user: their profile, their installations, and their latest reviews.

    The support view — "why is PRLens not reviewing my repo" is answered by whether
    the repo is here at all, and whether it is active.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    installations = db.query(Installation).filter(
        Installation.user_id == user.id
    ).order_by(Installation.installed_at.desc()).all()

    reviews = (
        db.query(Review)
        .options(joinedload(Review.installation))
        .join(Installation)
        .filter(Installation.user_id == user.id)
        .order_by(Review.reviewed_at.desc())
        .limit(min(limit, ADMIN_PAGE_LIMIT))
        .all()
    )

    review_counts, last_reviews = _reviews_per_user(db)

    # `repos` and `reviews` stay the counts they are on /api/admin/users — the lists
    # get their own keys rather than shadowing them with a different type.
    return {
        **serialize_admin_user(
            user,
            len(installations),
            review_counts.get(user.id, 0),
            last_reviews.get(user.id),
        ),
        "installations": [serialize_repo(installation) for installation in installations],
        "recentReviews": [serialize_review(review) for review in reviews],
    }