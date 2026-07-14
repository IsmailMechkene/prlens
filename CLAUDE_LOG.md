# Claude Log

## 2026-07-14 — Enabled PRLens from a second GitHub account, PR never got reviewed

**Q:** I logged in from another GitHub account (Kurasaki-67), enabled PRLens on a repo
(`Kurasaki-67/test`), but when I opened a PR it did not get reviewed. (The logs show no
`POST /webhook` after the enable.)

**A:** Two separate causes, neither of them in the review pipeline.

1. **"Enable" never installs the GitHub App.** `enable_repo` only inserts an
   `Installation` row in the database. It creates no webhook and does not install the
   PRLens App on the account, so GitHub had no reason to send anything for
   `Kurasaki-67/test`. Confirmed against the live GitHub API: the App is **not**
   installed on `Kurasaki-67/test` (it is on `IsmailMechkene/proposal`).
2. **The App was hardwired to one account.** `GitHubClient._auth_as_github_app` read a
   single `GITHUB_APP_INSTALLATION_ID` (144367286 — the IsmailMechkene installation).
   Even once the webhook fired, that token cannot see another account's repo, so posting
   the review would 404.

Fixes (branch `worktree-per-repo-installation-token`, draft PR):
- The client resolves the installation **per repo** via `GET /repos/{repo}/installation`,
  and raises a plain-English error when the App is not installed there.
  `GITHUB_APP_INSTALLATION_ID` is now GitHub-Actions-mode only.
- `/enable` returns `appInstalled` + `installUrl`, and the dashboard sends the user to
  GitHub to install the App instead of landing on a settings page that reviews nothing.

**Action still needed by you:** install the PRLens App on the Kurasaki-67 account
(https://github.com/apps/prlens-reviewer/installations/new) and grant it access to `test`.
