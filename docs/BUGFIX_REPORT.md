# PRLens Bugfix Report

Logic-bug audit of the dashboard backend (`prlens/webhook/app.py`, plus
`auth/github_oauth.py` which it calls) and the frontend (`dashboard/src/`).
Fixes only — no features, no styling, no refactors of working code.

**15 bugs found and fixed.** Verification: `ruff` clean on every changed Python
file, `pytest` 69/69 passing, `tsc --noEmit` and `eslint` clean.

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
  engine in a `finally`, on every path including exceptions. No leak.
- **`run_agent` with `DATABASE_URL` unset.** `_repo_config` returns `None` and the
  agent falls back to `load_settings()`; `_persist_review` logs and returns. Correct.

---

## Remaining known limitations

- **Set `SESSION_SECRET` in production.** With fix #1 an unset secret means a
  random per-process key, so sessions break across restarts *and across replicas*.
  That is deliberate (a forgeable constant is worse), but it is a misconfiguration
  the app can only degrade around, not repair.
- **`GET /api/github/repos` is not paginated** (`per_page=100`). Users with more
  than 100 repos cannot see the rest on the Connect page.
- **Shared repos have no settings arbitration.** With fix #7 the settings used are
  those of the lowest-id *active* installation — first connector wins. Two users
  with different settings on the same repo is still an unresolved product question.
- **A fresh engine and connection pool per background task.** Correct (and disposed),
  but a new pool per webhook event is wasteful. Fixing it means a module-level
  background engine — a refactor, out of scope here.
- **`scoreDelta` renders a hard-coded ▲** even when negative ("▲ -4 pts"). It is a
  display bug, and the brief excludes UI changes.
- **A failed settings save has no error UI** — the button just returns to
  "Save changes". A 401 now re-authenticates (fix #4); other failures are silent.
- **GitHub handle collisions.** `users.handle` is unique; a user who renames
  themselves on GitHub to a handle already in the table hits an `IntegrityError`
  on login. Also, an existing user's `name`/`handle`/`avatar_url` are never
  refreshed after the first sign-in.
- **Pre-existing `ruff` findings (28) are untouched.** They sit in `tests/` (which
  the brief forbids modifying), `eval/`, `main.py` and `database/connection.py` —
  all outside the reviewed scope, and all import-ordering / unused-import noise
  rather than logic. Every file this audit changed is `ruff`-clean; the baseline
  was 29, so the count went down by one (`auth/github_oauth.py`).
