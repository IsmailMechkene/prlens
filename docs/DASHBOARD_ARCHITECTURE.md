# PRLens Dashboard Architecture

How the whole system fits together: the review agent, the FastAPI backend, the
database, and the React dashboard.

This document describes the system as built. Where something is a known sharp
edge, it is called out in [Known limitations](#known-limitations-and-future-work)
rather than glossed over.

---

## 1. System overview

PRLens has four pieces. They are deliberately loosely coupled — the agent knows
nothing about the dashboard, and the dashboard never talks to the agent.

```
                  ┌──────────────────────────────────────┐
   GitHub  ──────▶│  POST /webhook   (FastAPI)           │
   (pull_request  │    verify HMAC signature             │
    event)        │    debounce + in-flight guard        │
                  │    schedule BackgroundTask           │
                  └────────────────┬─────────────────────┘
                                   │ run_agent() on a worker thread
                                   ▼
                  ┌──────────────────────────────────────┐
                  │  Agent (prlens/core/agent.py)        │
                  │    PRFetcher  → fetch + map the PR   │
                  │    Analyzer   → LLM review           │
                  │    PRPublisher→ labels, comments,    │
                  │                 summary, review      │
                  │  returns (PR, ReviewResult)          │
                  └────────────────┬─────────────────────┘
                                   │ _persist_review()
                                   ▼
                  ┌──────────────────────────────────────┐
                  │  Database (SQLAlchemy)               │
                  │  users ─ installations ─ reviews ─   │
                  │                      review_comments │
                  └────────────────┬─────────────────────┘
                                   │ read
                                   ▼
                  ┌──────────────────────────────────────┐
                  │  REST API  /api/*  (same FastAPI app)│
                  └────────────────┬─────────────────────┘
                                   │ fetch(credentials: 'include')
                                   ▼
                  ┌──────────────────────────────────────┐
                  │  React dashboard (Vite, :5173)       │
                  └──────────────────────────────────────┘
```

**Who owns what**

| Component | Location | Responsibility |
| --- | --- | --- |
| Agent | `prlens/core/agent.py` | Orchestrates fetch → analyze → publish. Pure pipeline; no DB, no HTTP server. |
| Publisher | `prlens/github/pr_publisher.py` | Decides the review *outcome* and writes it to the PR. |
| Web app | `prlens/webhook/app.py` | Webhook receiver, OAuth, REST API, review persistence. |
| Models | `database/models.py` | The four tables. |
| Dashboard | `dashboard/` | React + TypeScript SPA. |

The single most important structural fact: **the FastAPI app is both the webhook
receiver and the dashboard's API server.** They share a process, a database, and
a `.env`, but not a request lifecycle — see [§3.2](#32-why-the-background-task-opens-its-own-session).

---

## 2. Authentication flow

PRLens uses GitHub OAuth (the *web application flow*) with a signed,
cookie-backed session. There are no passwords and no JWTs.

### 2.1 Step by step

1. **The browser hits a protected route.** `RequireAuth`
   (`dashboard/src/components/layout/RequireAuth.tsx`) wraps `/dashboard`,
   `/repos/:name` and `/connect`. On mount it calls `GET /api/user`.

2. **No session → 401.** `get_current_user` finds no `user_id` in the session
   and raises `HTTPException(401)`. The API client turns any non-2xx into an
   `ApiError` carrying `status`.

3. **The guard redirects.** Seeing `ApiError.status === 401`, `RequireAuth` sets
   `window.location.href = ${VITE_API_BASE_URL}/auth/github`. This is a full page
   navigation, not a router push — we are leaving the SPA.

4. **`GET /auth/github`** returns a redirect to
   `https://github.com/login/oauth/authorize?client_id=…&scope=repo`.

5. **The user approves on GitHub**, which redirects back to the app's registered
   callback with a short-lived `?code=…`.

6. **`GET /auth/callback`** does three things:
   - `exchange_code_for_token(code)` → POSTs the code + client secret to GitHub,
     receives an **access token**.
   - `get_github_user(token)` → `GET https://api.github.com/user`.
   - Upserts the `users` row keyed on `github_id`, and **stores the access token
     in `users.github_token`**.

7. **The session is established.** `request.session["user_id"] = user.id`.
   Starlette's `SessionMiddleware` serialises the session dict, signs it with
   `SESSION_SECRET`, and sets it as the `session` cookie.

8. **Back to the dashboard.** The callback redirects to `${FRONTEND_URL}/dashboard`.
   Every subsequent `fetch` sends the cookie because the API client sets
   `credentials: 'include'`.

### 2.2 Where tokens live

| Secret | Stored | Lifetime |
| --- | --- | --- |
| GitHub OAuth access token | `users.github_token`, **plaintext** column | Until revoked |
| Session cookie | Browser; signed (not encrypted) with `SESSION_SECRET` | Browser session |
| `GITHUB_OAUTH_CLIENT_SECRET` | `.env`, server-side only | — |
| `GITHUB_WEBHOOK_SECRET` | `.env`, used for HMAC verification | — |

The cookie is *signed, not encrypted*: it proves the `user_id` was issued by us,
but anyone with the cookie can read it. It carries no token, only the row id.

The stored `github_token` exists for exactly one reason: `GET /api/github/repos`
needs to list repos **as the user**, including ones PRLens has never seen. Without
persisting it, repo discovery is impossible (see limitations).

### 2.3 CORS and cookies

Vite serves the dashboard on `:5173`; FastAPI listens on `:8000`. Every API call
is therefore **cross-origin**, and every API call carries a cookie. That requires:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],   # explicit; "*" is illegal with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Two subtleties worth knowing:

- **`allow_origins` cannot be `"*"` when `allow_credentials=True`.** Browsers
  reject the combination. The origin must be echoed back exactly, which is why
  `FRONTEND_URL` drives both the CORS allow-list and the post-OAuth redirect.
- **The cookie still works despite the port difference.** `SameSite=Lax` is
  scoped to the *site* (scheme + registrable domain), and ports are not part of
  a site. `localhost:5173` and `localhost:8000` are same-site, cross-origin.

---

## 3. Data flow: from pull request to dashboard row

### 3.1 The happy path

1. A developer opens PR #482 on `acme/api-gateway`.
2. GitHub POSTs a `pull_request` event to `/webhook` with an
   `X-Hub-Signature-256` header.
3. `verify_signature` recomputes the HMAC-SHA256 of the raw body using
   `GITHUB_WEBHOOK_SECRET` and compares with `hmac.compare_digest`. Mismatch → `403`.
4. Non-`pull_request` events, and actions other than `opened` / `synchronize` /
   `reopened`, are acknowledged and ignored.
5. `run_agent` is handed to `BackgroundTasks`. The endpoint returns
   `{"status": "accepted"}` immediately — GitHub gets its 2xx well inside the
   timeout, and the LLM work happens off the request.
6. `run_agent` takes two guards under a lock, both keyed on `"{repo}#{number}"`:
   - **in-flight:** the same PR is already being reviewed → skip.
   - **debounce:** the same PR finished less than `DEBOUNCE_SECONDS` (30s) ago →
     skip. This absorbs the burst of `synchronize` events from a rapid push.
7. The pipeline is constructed and `agent.run(...)` executes:
   fetch the PR → analyze each changed file with the LLM → apply labels, post the
   summary, post inline comments, submit the review, assign reviewers.
   It returns `(PR, ReviewResult)`.
8. `_outcome_to_status(result, pr_publisher)` asks the publisher which verdict it
   just submitted, and `_persist_review` writes one `reviews` row plus one
   `review_comments` row per finding.
9. The dashboard, on its next load, reads those rows through `/api/*`.

### 3.2 Why the background task opens its own session

This is the single easiest thing to get wrong in this codebase.

`BackgroundTasks` runs `run_agent` **on a worker thread**, after the request has
completed. The request-scoped session yielded by `Depends(get_db)` is closed in
that dependency's `finally` block the moment the response is returned. A
SQLAlchemy `Session` is also not thread-safe.

So a background task must never accept `db: Session = Depends(get_db)`. Instead
`_persist_review` builds a short-lived engine and session that it owns end to end:

```python
engine = create_engine(db_url)
local_session = sessionmaker(bind=engine)
db = local_session()
try:
    ...
    db.commit()
finally:
    db.close()
    engine.dispose()          # don't leak the pool
```

### 3.3 Failure containment

By the time `_persist_review` runs, the review is **already live on the pull
request**. A database problem must not turn that into a crashed task, so the
persistence block is wrapped:

```python
review_output = agent.run(repo_name, pr_number, actor)
try:
    pr, result = review_output
    _persist_review(repo_name, pr, result, _outcome_to_status(result, pr_publisher))
except Exception:
    logger.exception("Could not store review for %s", pr_key)
```

The dashboard row is a best-effort mirror of what GitHub already shows. The
in-flight marker is cleared in an outer `finally`, so a failure never wedges a PR
into a permanently "processing" state.

`_persist_review` is a no-op (with a log line) when `DATABASE_URL` is unset, or
when no **active** installation matches the repo.

### 3.4 Review status

`Review.status` stores the value of the agent's `ReviewOutcome` enum
(`prlens/github/pr_publisher.py`) — the same verdict that was posted to the PR:

| Status | Meaning |
| --- | --- |
| `approved` | Score above the approve threshold, no critical issues. |
| `changes_requested` | Score below the changes threshold, or a critical issue. |
| `comment` | Reviewed; nothing blocking. Also covers "no reviewable files". |
| `incomplete` | Some files failed to analyze. |
| `total_failure` | Every file failed to analyze (rate limit, outage, misconfig). |

`_outcome_to_status` takes the `PRPublisher` rather than recomputing the
thresholds, so the stored status can never disagree with the posted review.
The frontend renders these through `statusMeta()` in `src/lib/reviewStyles.ts`.

---

## 4. API reference

All REST endpoints are mounted under `/api` and **require a session cookie**;
without one they return `401`. The OAuth and webhook routes are unauthenticated
(the webhook authenticates via HMAC instead).

A repo `{name}` is always the GitHub **full name** (`acme/api-gateway`). Because
it contains a slash, the client must `encodeURIComponent` it and the routes use
FastAPI's `:path` converter. The bare `/api/repos/{name:path}` route is
**registered last** on purpose — a greedy path converter declared first would
swallow the `/reviews`, `/settings`, `/active` and `/enable` suffixes.

### Unauthenticated

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health check → `{"status":"ok","service":"PRLens"}` |
| `POST` | `/webhook` | GitHub `pull_request` events; HMAC-verified |
| `GET` | `/auth/github` | Redirect into the GitHub OAuth flow |
| `GET` | `/auth/callback` | OAuth callback; sets the session, redirects to the dashboard |

### The dashboard endpoints

| # | Method | Path | Called by |
| --- | --- | --- | --- |
| 1 | `GET` | `/api/user` | `Sidebar`, `RequireAuth` |
| 2 | `GET` | `/api/repos` | `Sidebar` |
| 3 | `GET` | `/api/stats` | `DashboardPage` |
| 4 | `GET` | `/api/reviews?limit=` | `DashboardPage` |
| 5 | `GET` | `/api/github/repos` | `ConnectPage` |
| 6 | `GET` | `/api/repos/{name}` | `RepoDetailPage` |
| 7 | `GET` | `/api/repos/{name}/reviews` | `RepoDetailPage` |
| 8 | `PUT` | `/api/repos/{name}/settings` | `ReviewSettings` |
| 9 | `PUT` | `/api/repos/{name}/active` | `RepoDetailPage` toggle |
| 10 | `POST` | `/api/repos/{name}/enable` | `ConnectRepoRow` |

---

#### 1. `GET /api/user`

The signed-in user. Doubles as the auth probe.

```json
{ "name": "Dana Kessler", "handle": "@dkessler", "initials": "DK", "avatarUrl": "https://…" }
```

#### 2. `GET /api/repos`

Installations belonging to the current user — i.e. repos PRLens already knows
about. Drives the sidebar list.

```json
[{ "name": "acme/api-gateway", "owner": "acme", "visibility": "Private",
   "updated": "2h ago", "connected": true, "active": true }]
```

#### 3. `GET /api/stats`

Three pre-formatted metric tiles. `value` is already a display string.

```json
{ "stats": [ { "id": "repos", "label": "Repos connected", "value": "4",
              "delta": "", "trend": "neutral", "icon": "git-branch",
              "iconColor": "var(--pa)" } ] }
```

Counts: installations for the user; reviews joined through them; review comments
joined through those.

#### 4. `GET /api/reviews?limit=10`

The user's most recent reviews across all repos, newest first.

```json
[{ "repo": "acme/api-gateway", "number": 482, "title": "Add JWT auth middleware",
   "score": 42, "status": "changes_requested", "reviewedAt": "2h ago" }]
```

#### 5. `GET /api/github/repos`

Every repo the user can see **on GitHub** (`per_page=100&sort=updated`), each
flagged with whether PRLens is already installed. This is the only endpoint that
uses the stored `github_token`, and the only one that can surface a repo with no
`installations` row — which is what makes "connect a new repo" possible.

Returns `401` if no token is stored. Note the absence of `active`: a repo with no
installation has no active flag.

```json
[{ "name": "acme/api-gateway", "owner": "acme", "visibility": "Private",
   "updated": "2h ago", "connected": false }]
```

#### 6. `GET /api/repos/{name}`

Full detail for one repo: the `Repo` fields plus description, score trend,
current score, issue breakdown and settings. `404` if the user has no
installation for that repo.

```json
{ "name": "acme/api-gateway", "owner": "acme", "visibility": "Private",
  "updated": "2h ago", "connected": true, "active": true,
  "description": "", "scoreTrend": [72, 75, 80], "currentScore": 80,
  "scoreDelta": 8,
  "issues": [{ "category": "Security", "value": 8 }],
  "settings": { "minSeverity": "warning",
                "languages": { "Python": true, "JavaScript": false,
                               "TypeScript": true, "Java": false },
                "approveThreshold": 80, "changesThreshold": 50,
                "excluded": ["*.lock"],
                "reviewerMap": [{ "key": "security", "value": "@acme/appsec" }] } }
```

`scoreTrend` is the daily mean score over the trailing 30 days, oldest first.
It is grouped in Python rather than SQL because `CAST(… AS DATE)` is not portable
to SQLite. `scoreDelta` is `currentScore − scoreTrend[0]`.

#### 7. `GET /api/repos/{name}/reviews`

Every review for one repo, newest first. Same `Review` shape as endpoint 4.

#### 8. `PUT /api/repos/{name}/settings`

Body is the full `settings` object from endpoint 6; returns it back as stored.
`approveThreshold` and `changesThreshold` are validated to `0–100`, and
`minSeverity` to the `Severity` enum — a bad value is a `422`, not a silently
corrupted row.

`languages` is sent as a display-name map (`{"Python": true}`) and stored as the
enum values of the enabled languages (`["python"]`).

#### 9. `PUT /api/repos/{name}/active`

```json
// request
{ "active": false }
// response
{ "active": false }
```

Pausing a repo stops `_persist_review` from recording its reviews, because that
lookup filters on `active`. It does **not** stop the webhook from reviewing the
PR (see limitations).

#### 10. `POST /api/repos/{name}/enable`

```json
// request
{ "owner": "acme", "visibility": "Private" }
```

Creates the installation if absent (seeding thresholds and languages from the
agent's own `Settings()` defaults), or flips `connected` / `active` back on if it
already exists. Returns the `Repo`. `visibility` is a `Literal["Public","Private"]`,
so a lowercase `"public"` is rejected with `422` rather than persisted forever.

---

## 5. Database schema

Four tables, defined in `database/models.py`. In plain English:

> A **user** signs in once. They install PRLens on any number of repos — each of
> those is an **installation**, which also stores that repo's review settings.
> Every time the agent reviews a pull request it writes one **review** row against
> the installation, and one **review comment** row for each individual finding.

```
users 1───∞ installations 1───∞ reviews 1───∞ review_comments
```

Every relationship cascades on delete: removing a user removes their
installations, their reviews, and those reviews' comments.

### `users`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | PK | |
| `github_id` | int, unique, indexed | The join key against GitHub, not `handle` |
| `name`, `handle`, `initials` | str | `handle` is `@login`; `initials` is the avatar fallback |
| `avatar_url` | text, nullable | |
| `github_token` | text, nullable | OAuth access token, plaintext |

### `installations`

One row per (user, repo). This is where per-repo configuration lives, so two
users who both install the same repo get independent settings.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | PK | |
| `user_id` | FK → `users.id` | `ON DELETE CASCADE` |
| `repo_name` | str | GitHub `full_name`, e.g. `acme/api-gateway` |
| `owner`, `visibility`, `description` | str | |
| `connected` | bool | PRLens is installed |
| `active` | bool | Reviewing is currently enabled |
| `min_severity` | str | `Severity` value |
| `languages` | JSON | Enabled `SupportedLanguages` values |
| `approve_threshold`, `changes_threshold` | int | 0–100 |
| `excluded_files` | JSON | Glob list |
| `reviewer_map` | JSON | `{review_type: reviewer}` |
| `installed_at` | datetime (tz-aware) | Rendered as `updated` |

Constraint: `UNIQUE (user_id, repo_name)`.

### `reviews`

One row per completed agent run against a PR. A PR reviewed three times produces
three rows — this table is an append-only history, which is exactly what the
trend chart needs.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | PK | |
| `installation_id` | FK → `installations.id` | `ON DELETE CASCADE` |
| `pr_number`, `pr_title` | int / str | |
| `score` | int | 0–100 |
| `status` | str | The `ReviewOutcome` value; see [§3.4](#34-review-status) |
| `reviewed_at` | datetime | **Naive UTC** (`datetime.utcnow`), unlike `installed_at` |

The naive/aware split is a real inconsistency: `score_trend` has to compare
against a naive bound (`datetime.now(timezone.utc).replace(tzinfo=None)`) because
of it.

### `review_comments`

One row per finding. Feeds the issue-breakdown donut, grouped by `type`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | PK | |
| `review_id` | FK → `reviews.id` | `ON DELETE CASCADE` |
| `file_path` | text | |
| `line` | int, NOT NULL | File-level findings have no line; stored as `0` |
| `type` | str | `ReviewType` value |
| `severity` | str | `Severity` value |
| `message` | text | |
| `suggestion` | text, nullable | |

---

## 6. Frontend routing

React Router, defined in `dashboard/src/App.tsx`.

| URL | Page | Guarded | Data fetched on mount |
| --- | --- | --- | --- |
| `/` | `LandingPage` | no | none (static marketing copy) |
| `/dashboard` | `DashboardPage` | yes | `GET /api/stats`, `GET /api/reviews` |
| `/repos/:name` | `RepoDetailPage` | yes | `GET /api/repos/{name}`, `GET /api/repos/{name}/reviews` |
| `/connect` | `ConnectPage` | yes | `GET /api/github/repos` |
| `*` | → redirect to `/` | — | — |

The three guarded routes sit inside `<RequireAuth>` → `<AppLayout>`. `AppLayout`
renders the persistent `Sidebar`, which independently fetches `GET /api/user` and
`GET /api/repos`.

`:name` holds a URL-encoded `owner/repo`. Every link builds it with
`encodeURIComponent` — otherwise the slash creates a second path segment, the
route fails to match, and the `*` fallback bounces the user to the landing page.

### Data fetching

`useAsync(fn, deps)` (`src/lib/useAsync.ts`) is a ~40-line hook: runs `fn` on
mount and whenever `deps` change, tracks `{data, loading, error}`, guards against
`setState` after unmount, and exposes `reload()`. `<AsyncBoundary state={…}>`
renders the spinner / error+retry / content branches from that state.

### Mock mode

`src/lib/api.ts` reads `VITE_API_BASE_URL`. **When it is unset, every method
returns fixtures from `src/lib/mockData.ts`** behind a 250 ms delay, so the whole
UI — including loading states — is usable with no backend at all. `RequireAuth`
is inert in this mode, since there is nothing to authenticate against.

When it *is* set, it is treated as an **origin**: REST calls go to
`${BASE}/api/*` and the OAuth entrypoint is `${BASE}/auth/github`.

---

## 7. Local development setup

You need three processes: the API, the dashboard, and (only if you want real
webhooks) a tunnel.

### 7.1 Environment

`.env` at the repo root, read by the backend:

```bash
DATABASE_URL=sqlite:///./prlens.db     # or a Postgres URL
GITHUB_WEBHOOK_SECRET=<random string, must match the GitHub App>
GITHUB_OAUTH_CLIENT_ID=<from the OAuth App>
GITHUB_OAUTH_CLIENT_SECRET=<from the OAuth App>
SESSION_SECRET=<random string>
FRONTEND_URL=http://localhost:5173     # optional; this is the default

# The agent itself
GITHUB_APP_ID=…
GITHUB_APP_INSTALLATION_ID=…
GITHUB_APP_PRIVATE_KEY_PATH=…
AZURE_OPENAI_API_KEY=…
AZURE_OPENAI_ENDPOINT=…
```

`dashboard/.env.local`, read by Vite:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Delete that line to run the dashboard entirely on mock data.

### 7.2 Backend

```bash
pip install -r requirements.txt
uvicorn prlens.webhook.app:app --reload --port 8000
```

`init_db()` runs in the lifespan handler, so the tables are created on first
start. Check it: `curl http://localhost:8000/` → `{"status":"ok",…}`.

### 7.3 Dashboard

```bash
cd dashboard
npm install
npm run dev          # http://localhost:5173
```

Visit `http://localhost:5173/dashboard`. With no session you are bounced through
GitHub OAuth and land back on the dashboard.

### 7.4 OAuth app configuration

In your GitHub **OAuth App** settings set the callback URL to:

```
http://localhost:8000/auth/callback
```

It points at the **backend**, not the dashboard — the backend needs the `?code`
to exchange server-side with the client secret. The backend then redirects the
browser to `FRONTEND_URL/dashboard`.

### 7.5 Webhooks via ngrok

GitHub cannot reach `localhost`, so to exercise the real review path:

```bash
ngrok http 8000
```

Take the public HTTPS URL and, in your **GitHub App** → *Webhooks*:

- **Payload URL:** `https://<subdomain>.ngrok-free.app/webhook`
- **Content type:** `application/json`
- **Secret:** the same value as `GITHUB_WEBHOOK_SECRET`
- **Events:** *Pull requests* only

Open a PR on a repo you have enabled in the dashboard. Watch the uvicorn log:
the endpoint returns `accepted` immediately, then the agent runs on a background
thread and the review appears on the PR. Reload `/dashboard` to see the row.

If nothing appears in the dashboard but the PR *was* reviewed, the cause is
almost always that no **active installation** matches the repo — look for
`No active installation for … ; review not stored` in the log.

### 7.6 Checks

```bash
ruff check prlens/            # lint
pytest                        # 69 tests
cd dashboard && npx tsc --noEmit && npx eslint .
```

---

## 8. Known limitations and future work

These are real, and mostly deliberate trade-offs rather than oversights.

**Auth**

- **Token expiry is unhandled.** `users.github_token` is stored once and never
  validated. When GitHub expires or the user revokes it, `GET /api/github/repos`
  starts returning a GitHub error body. The `isinstance(r, dict)` guard stops
  that from crashing the endpoint, but the user silently sees an empty repo list
  instead of being asked to re-authenticate. It should detect the `401` from
  GitHub and re-trigger the OAuth flow.
- **No refresh token.** The OAuth flow requests none, so there is no way to renew
  a token without user interaction.
- **The token is stored in plaintext.** Anyone with read access to the database
  gets `repo`-scoped access to every connected user's repositories. It should be
  encrypted at rest with a key held outside the DB.
- **The session is single-user and process-local in spirit.** The cookie is
  signed but not encrypted, has no explicit expiry, and there is no logout
  endpoint or session revocation list. Rotating `SESSION_SECRET` is the only way
  to invalidate every session at once.
- **`SESSION_SECRET` has an insecure default** (`"dev-secret-change-in-production"`).
  A deployment that forgets to set it has forgeable sessions. It should fail
  loudly at startup instead.

**Repo discovery and ownership**

- **Discovery depends entirely on the stored token.** `GET /api/github/repos` is
  the only path by which a repo with no `installations` row can appear in the UI.
  No token → no discovery → the Connect page is empty.
- **The repo list is capped at 100** (`per_page=100`) and not paginated.
- **`_persist_review` resolves the installation by `repo_name` alone**, taking the
  first *active* match. If two users install the same repo, the review is
  attributed to whichever row the database returns first. The webhook payload has
  no notion of "which PRLens user this is for", so fixing this properly means
  keying installations on the GitHub App installation id.

**Review pipeline**

- **Pausing a repo does not stop reviews.** `active: false` only suppresses
  *persistence* — the webhook still runs the agent and still comments on the PR.
  `run_agent` should check the installation before doing any work.
- **Per-repo settings are not applied by the agent.** `run_agent` calls
  `load_settings()`, which reads the repo's `.aireviewer.yml` / defaults. The
  thresholds, excluded files and reviewer map edited in the dashboard are stored
  in `installations` and *read back by the dashboard*, but never fed into the
  agent run. Wiring these together is the most valuable next change.
- **Debounce state is in-process.** `_processing_prs` and `_last_processed` are
  module-level dicts behind a `threading.Lock`. They do not survive a restart and
  are not shared across workers, so running uvicorn with `--workers 2` gives you
  duplicate reviews. A shared store (Redis) or a DB advisory lock is needed.
- **`_persist_review` opens a new engine per review.** Correct and safe, but it
  discards connection pooling. At volume, a module-level thread-safe
  `sessionmaker` would be better.

**Data**

- **`reviews.reviewed_at` is naive UTC** while `installations.installed_at` is
  timezone-aware. They should agree.
- **`scoreTrend` is computed in Python** over every review in a 30-day window.
  Fine at current volume; it should become a SQL aggregate.
- **There are no schema migrations.** `init_db()` calls `create_all`, which adds
  missing tables but never alters existing ones. Adding a column to a live
  database requires Alembic.
