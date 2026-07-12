# PRLens Bugfix Report

Logic-bug audit of the dashboard backend (`prlens/webhook/app.py`, plus
`auth/github_oauth.py` which it calls) and the frontend (`dashboard/src/`).

**15 bugs found and fixed** in the first pass, then **7 follow-ups** that closed
the limitations that pass had left open (part 2 below).

Verification: `ruff` passes repo-wide, `pytest` 69/69, `tsc --noEmit` and `eslint`
clean. The backend fixes were also driven end-to-end against a throwaway SQLite
database rather than only type-checked — see the notes under each item.

---

# Part 1 — the audit

---

## High severity

### 1. Session tokens are forgeable when `SESSION_SECRET` is unset

**File:** `prlens/webhook/app.py` (`JWT_SECRET`)

`JWT_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-in-production")`.
A deployment that forgets the variable signs and verifies every session JWT with
a constant that is committed to this repository.

**Without the fix:** anyone who can read the source can mint
`{"user_id": 1}` signed with the known secret and impersonate any account —
full read/write access to that user's repos, reviews and settings. It fails
open and silently: nothing in the logs or the UI says the app is unprotected.

**Fix:** an unset secret now falls back to a random per-process key and logs a
warning. Forged tokens become impossible; the cost of a missing variable drops
to "sessions don't survive a restart", which is a login prompt, not a takeover.

---

### 2. OAuth callback returns 500 on a reused or expired code

**Files:** `auth/github_oauth.py` (`exchange_code_for_token`), `prlens/webhook/app.py` (`github_callback`)

`exchange_code_for_token` did `data["access_token"]`. When GitHub rejects a code
it still answers **HTTP 200**, with `{"error": "bad_verification_code", ...}` in
the body — so the status code alone cannot distinguish success from failure, and
the subscript raised `KeyError`.

**Without the fix:** reloading `/auth/callback`, pressing back into it, or taking
more than 10 minutes over the GitHub consent screen produces a bare
`500 Internal Server Error` with a stack trace, and the user cannot sign in. The
same `KeyError` path is hit if GitHub returns an error object from `/user`.

**Fix:** `exchange_code_for_token` raises a typed `OAuthError` carrying GitHub's
`error_description`; the callback maps it to `400` with a readable message, and
also validates that the `/user` response really is a profile before reading
`id`/`login` from it.

---

### 3. Frontend white-screens when `localStorage` is unavailable

**File:** `dashboard/src/lib/api.ts` (`getToken` / `captureAuthToken`)

Storage access was unguarded. Reading `window.localStorage` throws a
`SecurityError` when the browser blocks storage (some private-browsing modes,
third-party-cookie-blocked iframes, "block all cookies" settings), and
`setItem` can throw a quota error even where reading works.

**Without the fix:** `captureAuthToken()` runs in `main.tsx` **before**
`createRoot(...).render(...)`. The throw happens before React ever mounts, so
the user gets a blank white page with no error boundary and no way to recover —
the entire app is dead, not just persistence.

**Fix:** a `SafeStore` wrapper around `localStorage`/`sessionStorage` catches
every access and falls back to an in-memory `Map`. A storage failure now costs
the user persistence across reloads instead of the whole application.

---

### 4. A 401 mid-session never re-authenticates

**Files:** `dashboard/src/lib/api.ts` (`request`), `dashboard/src/components/layout/RequireAuth.tsx`

`RequireAuth` only reacted to a 401 from its own `GET /api/user` probe on mount.
Every other call (`/stats`, `/repos`, `/reviews`, settings saves…) just threw an
`ApiError` into its `AsyncBoundary`.

**Without the fix:** when a 30-day token expires while the tab is open — or the
account behind it is deleted — the panels show "Couldn't load data" with a Retry
button that can only fail again, because the dead token stays in `localStorage`
and is resent on every retry. The user is stuck until they manually clear site
data.

**Fix:** `request()` treats 401 as an auth event wherever it occurs: it drops the
stale token and starts the OAuth redirect. `RequireAuth` no longer owns the
redirect, only what to paint while it is in flight.

---

### 5. Infinite OAuth redirect loop

**Files:** `dashboard/src/lib/api.ts` (`startLogin`), `dashboard/src/components/layout/RequireAuth.tsx`

The old guard redirected to `/auth/github` on *every* 401, unconditionally.

**Without the fix:** if the backend rejects even a freshly minted token — the
account row was deleted, or `SESSION_SECRET` differs between replicas, so a
token issued by one instance is invalid at the next — the browser bounces
dashboard → GitHub → dashboard → GitHub without end. Fix #4 widens the blast
radius (any endpoint can now trigger a redirect), so the guard is a prerequisite,
not an optional extra.

**Fix:** `startLogin()` allows at most one redirect per failing session, tracked
in `sessionStorage` and cleared by the first successful API response. A later,
legitimate expiry still re-authenticates normally; a broken backend lands on the
error state instead of a redirect storm. The same flag makes the several
simultaneous 401s from a page load (sidebar + stats + reviews) collapse into one
redirect rather than several racing `location.href` assignments.

---

### 6. Repo settings form keeps the previous repo's values — and saves them

**File:** `dashboard/src/pages/RepoDetailPage.tsx`

`RepoDetailContent` seeds `useState(detail.active)`, and `ReviewSettings` seeds
`useState(initial)`, from props. `useAsync` deliberately holds the previous data
while refetching, so `AsyncBoundary` keeps the subtree **mounted** across a
`:name` change — and mounted components ignore new seed values.

**Without the fix:** navigating from repo A to repo B (sidebar, breadcrumb, a
review row) leaves B's page showing A's active toggle and A's entire settings
form — severity, languages, thresholds, exclusions. Pressing **Save changes**
writes A's configuration onto B, silently changing how B's pull requests are
reviewed. This is the most damaging bug in the audit: it corrupts data during
ordinary navigation.

**Fix:** `key={data.name}` on `RepoDetailContent`, so a repo change remounts the
subtree and re-seeds both `useState` calls.

---

## Medium severity

### 7. One paused installation disabled reviewing for every other user

**File:** `prlens/webhook/app.py` (`_repo_config`)

The unique key is `(user_id, repo_name)`, so several users can connect the same
repo. `_repo_config` took an arbitrary `.first()` row and returned its `active`
flag and its settings.

**Without the fix:** if the row the database happened to return first belongs to
a user who paused the repo, `run_agent` logs "Paused" and skips the review — for
everyone, including users who have it switched on. Which settings get used is
likewise a coin toss, and can change between deploys.

**Fix:** query all installations for the repo in a deterministic order, treat the
repo as active when **any** installation is, and review with that installation's
settings.

---

### 8. Reviews lost: single-installation match, and over-long PR titles

**File:** `prlens/webhook/app.py` (`_persist_review`)

Two defects in one function. (a) It matched only one active installation with
`.first()`, so on a repo connected by two users the review landed on an
arbitrary one and the other user's dashboard stayed empty. (b) `Review.pr_title`
is `VARCHAR(255)` while GitHub allows 256-character titles — Postgres rejects an
over-long value with a `DataError` rather than truncating.

**Without the fix:** (b) fails the whole `INSERT`, so a PR with a long title is
reviewed on GitHub but never appears on the dashboard. The failure is invisible:
`run_agent` deliberately swallows persistence errors so they can't fail the
review, so it only ever shows up as a log line.

**Fix:** persist a `Review` row for every active installation of the repo, and
truncate the title to the column width. (`comment.line or 0` already covered the
`NOT NULL` line column for file-level comments — left as is.)

---

### 9. `enable_repo` is not idempotent under concurrency

**File:** `prlens/webhook/app.py` (`enable_repo`)

Check-then-insert with no handling of the losing race: both requests see no row,
both `INSERT`, and the `uq_user_repo` unique constraint rejects the second.

**Without the fix:** a double-click on **Enable PRLens**, or a retried request,
returns `500` from the loser — even though the repo *was* enabled by the winner.
The UI shows a failure for an operation that succeeded.

**Fix:** catch `IntegrityError`, roll back, re-read the row the winner committed
and update it. The endpoint is now genuinely idempotent.

---

### 10. A revoked GitHub token looks like "you have no repositories"

**File:** `prlens/webhook/app.py` (`get_github_repos`)

The response was passed to `response.json()` without checking the status. GitHub's
error body is a *dict*, so iterating it yields its keys (strings), and the
`isinstance(r, dict)` guard in the comprehension silently drops every one.

**Without the fix:** a user whose OAuth grant was revoked or expired sees an
empty Connect page — "no repositories" — with no error and no way to reconnect.

**Fix:** a non-200 from GitHub raises: `401` for an expired token (which the
frontend now turns into a re-login, per fix #4), `502` otherwise.

---

### 11. `get_current_user` crashes with 500 on a token without `user_id`

**File:** `prlens/webhook/app.py` (`get_current_user`)

`payload["user_id"]` was outside the `except` coverage — `ExpiredSignatureError`
and `InvalidTokenError` were handled, `KeyError` was not.

**Without the fix:** a correctly signed JWT that is not one of ours (e.g. minted
by another service sharing the secret, or an older token format) returns `500`
instead of `401`. A failed authentication must not read as a server fault.

**Fix:** `KeyError` also maps to `401 Invalid token`.

---

### 12. "Open on GitHub" links 404, and the title shows the owner twice

**File:** `dashboard/src/pages/RepoDetailPage.tsx`

The backend sends GitHub's `full_name` ("acme/api-gateway") as `name`, but the
page rendered `{detail.owner}/{detail.name}`.

**Without the fix:** the heading reads `acme/acme/api-gateway` and the header
link points at `https://github.com/acme/acme/api-gateway`, which 404s. (The bug
is invisible in mock mode, where the fixtures use a short name — which is why it
shipped.)

**Fix:** derive the full name once, tolerating both shapes:
`detail.name.includes('/') ? detail.name : `${detail.owner}/${detail.name}``.

---

## Low severity

### 13. A failing review crashes the background task

**File:** `prlens/webhook/app.py` (`run_agent`)

Only the persistence step was wrapped. An exception from `agent.run()` (GitHub
5xx, LLM timeout, malformed diff) escaped into Starlette's `BackgroundTasks`
runner *after* the webhook response was already sent, where it can only surface
as an unhandled ASGI error — no HTTP status can be produced for it any more.

**Fix:** wrap the pipeline, log with `logger.exception`, and return. The
in-flight marker is still cleared by the existing `finally`.

---

### 14. `_last_processed` grows without bound

**File:** `prlens/webhook/app.py` (`run_agent`)

Every PR ever seen kept an entry in the debounce dict for the lifetime of the
process; nothing ever removed one. A slow leak on a long-running server.

**Fix:** entries older than `DEBOUNCE_SECONDS` can no longer suppress anything,
so they are dropped when a new PR is marked in-flight.

---

### 15. `request()` could drop the `Authorization` header

**File:** `dashboard/src/lib/api.ts` (`request`)

`{ headers: {...merged}, ...init }` spread `init` **after** `headers`, so an
`init.headers` would have replaced the merged object wholesale — losing the
bearer token and `Content-Type`. Latent today (no caller passes headers), a
401-shaped mystery for the next one who does.

**Fix:** spread `init` first, `headers` last.

---

## Checked and found correct (no change made)

- **`get_repo` / `scoreDelta` with an empty trend.** `current_score - trend[0] if trend else 0`
  parses as `(current_score - trend[0]) if trend else 0` — the conditional binds
  looser than the subtraction, so `trend[0]` is never evaluated on an empty list.
  No `IndexError`.
- **Route registration order.** The four sub-routes (`/reviews`, `/settings`,
  `/active`, `/enable`) are all registered before the greedy
  `GET /api/repos/{name:path}`, which is last in the file. Sub-paths are not
  swallowed. `/api/repos` (list) and `/api/github/repos` are unaffected.
- **Engine lifecycle in `_repo_config` / `_persist_review`.** Both dispose their
  engine in a `finally`, on every path including exceptions. No leak. (They now
  share one pooled engine instead — see #16.)
- **`run_agent` with `DATABASE_URL` unset.** `_repo_config` returns `None` and the
  agent falls back to `load_settings()`; `_persist_review` logs and returns. Correct.

---

# Part 2 — closing the limitations

Part 1 left eight things open. Seven are now fixed; the eighth (`SESSION_SECRET`)
is deployment configuration, and is confirmed set on Railway.

---

### 16. One pooled engine for background tasks, not one per webhook event

**File:** `prlens/webhook/app.py` (`_background_session_factory`)

`_repo_config` and `_persist_review` each built a `create_engine(...)` and threw it
away again. An engine owns a *connection pool*, so every webhook event paid a fresh
TCP + TLS handshake to Postgres — twice — and discarded the pool immediately after.

**Fix:** one lazily-built, process-wide engine behind a lock, reused by both
functions, with `pool_pre_ping=True` so a connection the database dropped while the
pool sat idle between events is detected and replaced rather than handed out dead.
It rebuilds if `DATABASE_URL` changes, which in practice only happens under test.
`DATABASE_URL` unset still returns `None`, so the file-settings fallback is
untouched. Verified: two calls return the same factory object.

---

### 17. Shared repos: strictest-wins settings

**File:** `prlens/webhook/app.py` (`_merge_settings`)

Fix #7 made the choice deterministic (lowest-id active installation) but still
picked *one* user's settings and discarded everyone else's. Only one review is
posted to the pull request, so the configurations have to be reconciled — and
reconciling towards the **strictest** option is the only rule under which no user's
settings can be silently weakened by somebody else's:

| Field | Rule | Why |
|---|---|---|
| `min_severity` | lowest | a comment anyone wants to see survives |
| `target_languages` | union (empty ⇒ empty) | a language anyone reviews is reviewed; an empty list means "no filter", which is the strictest value, so it absorbs the rest |
| `excluded_files` | intersection | a file is skipped only if *everyone* skips it |
| `approve_threshold` | highest | hardest to approve |
| `changes_threshold` | highest | quickest to request changes |
| `reviewers_mapping` | merged, earliest installation wins a conflict | someone is always assigned |

Paused installations take no part. Verified against three installations (one lax,
one strict, one paused-but-strictest): the paused one is ignored, and every field
resolves as tabulated above.

---

### 18. `GET /api/github/repos` is now paginated

**File:** `prlens/webhook/app.py` (`get_github_repos`)

`per_page=100` with no `page` parameter: repositories beyond the hundredth simply
did not exist as far as the Connect page was concerned, with nothing in the UI to
suggest the list was truncated.

**Fix:** walk pages until GitHub returns a short one, with a 20-page runaway guard
(2000 repos) that logs if it is ever hit. Verified against a stubbed GitHub
returning 100 + 100 + 43: 243 repos returned, exactly 3 pages requested, and a
401 still surfaces as a 401 rather than an empty list.

---

### 19. A GitHub rename no longer breaks sign-in

**Files:** `database/models.py`, `database/connection.py` (`_relax_handle_uniqueness`), `prlens/webhook/app.py` (`github_callback`)

`users.handle` was `unique=True`. A handle is a *GitHub login*: it can be renamed,
and the old one can then be claimed by somebody else. Two rows converging on one
handle raised an `IntegrityError` — a 500 on an otherwise perfectly valid login,
and unfixable by the user. `github_id` is the real identity, and it is already
unique.

**Fix:** `handle` is indexed but no longer unique. `create_all()` never alters an
existing table, so `init_db()` runs an idempotent `_relax_handle_uniqueness()` at
boot that drops the legacy unique index (and, on Postgres, the constraint form)
and recreates a plain one. It is wrapped in `try/except` so a permissions problem
degrades to a log line rather than a failed boot. Verified against a database
seeded with the *old* unique index: after boot the index is plain, and two users
can hold `@alice`.

Also fixed here: an existing user's `name`, `handle`, `initials` and `avatar_url`
were captured at first sign-in and never updated. They are now refreshed on every
login, keyed on `github_id`.

---

### 20. `scoreDelta` renders the direction it actually has

**File:** `dashboard/src/pages/RepoDetailPage.tsx`

The arrow was a hard-coded `▲`, so a repo whose quality had *fallen* displayed
"▲ -4 pts" — in green.

**Fix:** `▲` / `▼` / `–` on the sign, `Math.abs()` on the number, and the colour
follows (`--success` / `--danger` / `--fg-muted`).

---

### 21. A failed settings save says so

**File:** `dashboard/src/components/repo/ReviewSettings.tsx`

`save()` had no `catch`. A rejected `PUT` left the button back on "Save changes"
with no other sign, so the user walked away believing a change had been stored
that had not — and the form still showed the values they thought they had saved.

**Fix:** a `failed` state replaces the hint line with "Couldn't save — nothing was
changed. Try again." (`role="alert"`, existing `saveHint` class, `--danger`). A
401 still re-authenticates via fix #4; this covers every other failure.

---

### 22. `ruff` passes repo-wide

Baseline was 29 findings; the audit's own files were always clean, but `tests/`,
`eval/`, `main.py` and `database/connection.py` carried import-ordering and
unused-import noise. All fixed (`ruff check --fix`), plus one manual `== True` →
`is True` in `tests/llm/test_analyzer.py`.

The test edits are import-ordering only — the removed `from tests.conftest import
...` lines were redundant re-imports of fixtures pytest already resolves through
`conftest.py`. All 69 tests still pass.

---

## Remaining known limitations

- **`SESSION_SECRET` must be set, and identical across replicas.** Unset, the app
  falls back to a random per-process key (fix #1) and warns at boot: sessions then
  break at the next restart and never work across replicas. That is deliberate — a
  published constant is worse — but it is a misconfiguration the app can only
  degrade around, not repair. **Confirmed set on Railway.** It is now documented in
  `.env.example`, along with the other dashboard variables that were missing from it
  (`DATABASE_URL`, `GITHUB_WEBHOOK_SECRET`, the OAuth pair, `FRONTEND_URL`).
- **Strictest-wins is not what everyone will want.** A user who connects a repo
  someone else has already connected inherits a stricter configuration than the one
  they set, and the dashboard does not tell them that their settings were merged
  rather than applied. Surfacing "these settings are shared with N other users" is
  a UI change, so it is out of scope here.
- **`_relax_handle_uniqueness` runs on every boot.** It is idempotent and cheap, but
  it is a migration living in application startup because the project has no
  migration tool. If Alembic is ever added, that is where this belongs.
- **The 20-page cap on `/api/github/repos`** (2000 repos) is a runaway guard, not a
  real limit — but a user above it would still silently see a truncated list. It
  logs when hit.
- **The dashboard fetches `/api/user` twice on load** (once in `RequireAuth`, once
  in `Sidebar`). Harmless — both are cheap and neither races — but redundant.
- **No test coverage for the new backend paths.** `_merge_settings`, the pagination
  loop and the handle migration were each verified end-to-end against a temporary
  SQLite database during this work, but that was throwaway scripting, not committed
  tests. The existing suite (69 tests) does not exercise them.
