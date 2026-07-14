import logging
from collections import Counter
from enum import Enum

from github import GithubException
from github.PullRequest import PullRequest

from prlens.config.settings import Settings
from prlens.github.client import GitHubClient
from prlens.models.review import (
    ReviewComment,
    ReviewResult,
    ReviewType,
    Severity,
)

logger = logging.getLogger(__name__)

class ReviewOutcome(Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENT = "comment"
    INCOMPLETE = "incomplete"
    TOTAL_FAILURE = "total_failure"

class PRPublisher:
    SUMMARY_MARKER = "<!-- prlens-summary -->"
    # Stamped on every finding PRLens posts, so a re-review can recognise its own
    # previous findings without having to work out who authored them. Kept distinct
    # from SUMMARY_MARKER: the summary is posted *before* the findings are cleared,
    # so a single marker would have the finding sweep delete the fresh summary.
    FINDING_MARKER = "<!-- prlens-finding -->"

    SEVERITY_EMOJI = {
        Severity.INFO: "🔵",
        Severity.WARNING: "🟡",
        Severity.ERROR: "🟠",
        Severity.CRITICAL: "🔴",
    }

    def __init__(self, client: GitHubClient, settings: Settings):
        self.client = client

        self.approve_threshold = settings.approve_threshold
        self.changes_threshold = settings.changes_threshold
        self.large_pr_threshold = settings.large_pr_threshold


    def _determine_review_outcome(self, result: ReviewResult) -> ReviewOutcome:
        if result.total_files == 0:
            return ReviewOutcome.COMMENT

        if len(result.failed_files) == result.total_files and result.total_files > 0 :
            return ReviewOutcome.TOTAL_FAILURE

        if (result.total_files > 0 and not result.comments and not result.positives
            and not result.recommendations and not result.failed_files):
            return ReviewOutcome.COMMENT

        if result.failed_files:
            return ReviewOutcome.INCOMPLETE

        if result.score > self.approve_threshold and not result.has_critical_issues:
            return ReviewOutcome.APPROVED

        if result.score < self.changes_threshold or result.has_critical_issues:
            return ReviewOutcome.CHANGES_REQUESTED

        return ReviewOutcome.COMMENT

    def determine_outcome(self, result: ReviewResult) -> ReviewOutcome:
        """The outcome this publisher would submit for ``result``.

        Exposed so callers that persist a review can record the same verdict
        that was posted to GitHub, rather than recomputing the thresholds.
        """
        return self._determine_review_outcome(result)

    def _determine_review_status(self, result: ReviewResult) -> str:
        outcome = self._determine_review_outcome(result)

        if outcome == ReviewOutcome.APPROVED:
            return "✅ Approved"

        if outcome == ReviewOutcome.CHANGES_REQUESTED:
            return "⚠️ Changes Requested"

        if outcome == ReviewOutcome.INCOMPLETE:
            return "🟣 Review Incomplete"

        if outcome == ReviewOutcome.TOTAL_FAILURE:
            return "⛔ Failed Review"

        return "ℹ️ Reviewed"

    def _build_summary(self, result: ReviewResult) -> str:
        badge = self._determine_review_status(result)

        outcome = self._determine_review_outcome(result)
        score_text = "N/A" if outcome in (ReviewOutcome.INCOMPLETE, ReviewOutcome.TOTAL_FAILURE) else f"{result.score}/100"

        severity_counts = Counter(comment.severity for comment in result.comments)

        severity_text = (
            "\n".join(
                f"- {severity.value}: {count}"
                for severity, count in severity_counts.items()
            )
            if severity_counts
            else "None"
        )

        positives_text = (
            "\n".join(f"- {positive}" for positive in result.positives)
            if result.positives
            else "None"
        )

        recommendations_text = (
            "\n".join(f"- {recommendation}" for recommendation in result.recommendations)
            if result.recommendations
            else "None"
        )

        return f"""
## PRLens Review Summary

{badge}

**Score:** {score_text}

### Issues by Severity
{severity_text}

### Positive Observations
{positives_text}

### Recommendations
{recommendations_text}
"""

    def _own_logins(self) -> set[str]:
        """The logins whose comments on a PR are PRLens's own.

        "github-actions[bot]" is unconditional: that is who the packaged Action
        posts as. The other is whoever this client authenticates as — the App's bot
        in the webhook deployment, the token's user for a PAT.
        """
        logins = {"github-actions[bot]"}
        login = self.client.get_authenticated_login()
        if login:
            logins.add(login)
        return logins

    def _is_own_finding(self, body: str | None, login: str | None, own: set[str]) -> bool:
        if self.FINDING_MARKER in (body or ""):
            return True
        # Findings posted before the marker existed carry no evidence but their
        # author, so fall back to that. Never matches a human: `own` is this
        # client's own identity, not anybody named in the webhook payload.
        return login in own

    def _delete_previous_findings(self, pull_request: PullRequest) -> None:
        own = self._own_logins()

        for comment in pull_request.get_review_comments():
            if self._is_own_finding(comment.body, comment.user.login, own):
                comment.delete()

        # A finding with no line, or one GitHub refused to attach to the diff, is
        # posted as an issue comment (see below). Those were never swept — only
        # *review* comments were — so every re-review left another copy behind.
        # The summary is an issue comment too, and post_summary has already put the
        # current one up by now, so it is explicitly spared.
        for comment in pull_request.get_issue_comments():
            body = comment.body or ""
            if self.SUMMARY_MARKER in body:
                continue
            if self._is_own_finding(body, comment.user.login, own):
                comment.delete()

    def _dismiss_previous_reviews(self, pull_request: PullRequest) -> None:
        own = self._own_logins()
        for review in pull_request.get_reviews():
            if review.user.login in own and review.state in ("APPROVED", "CHANGES_REQUESTED"):
                review.dismiss(message="Superseded by a new PRLens review.")

    def post_inline_comments(self, pull_request: PullRequest, comments: list[ReviewComment]) -> None:
        self._delete_previous_findings(pull_request)

        commit = pull_request.get_commits().reversed[0]

        for comment in comments:
            emoji = self.SEVERITY_EMOJI.get(comment.severity, "⚪")

            body = f"{self.FINDING_MARKER}\n{emoji} {comment.message}"

            if comment.suggestion:
                body += f"\n\n💡 **Suggestion:** {comment.suggestion}"

            if comment.line is None:
                pull_request.create_issue_comment(body=body)
            else:
                try:
                    pull_request.create_review_comment(
                        body=body,
                        commit=commit,
                        path=comment.file_path,
                        line=comment.line,
                    )
                except GithubException as e:
                    logger.warning("Could not post inline comment on %s:%s, falling back to issue comment: %s",
                                   comment.file_path, comment.line, e)
                    pull_request.create_issue_comment(body=body)

    def post_summary(self, pull_request: PullRequest, result: ReviewResult) -> None:
        summary = f"{self.SUMMARY_MARKER}\n{self._build_summary(result)}"

        for comment in pull_request.get_issue_comments():
            if self.SUMMARY_MARKER in (comment.body or ""):
                comment.delete()
                break

        outcome = self._determine_review_outcome(result)
        if not (outcome == ReviewOutcome.COMMENT and result.total_files == 0):
            pull_request.create_issue_comment(body=summary)

    def apply_labels(self, pull_request: PullRequest, result: ReviewResult) -> None:
        labels = []

        outcome = self._determine_review_outcome(result)

        if outcome == ReviewOutcome.APPROVED:
            labels.append("ai-approved")

        if outcome == ReviewOutcome.CHANGES_REQUESTED:
            labels.append("needs-changes")

        if outcome == ReviewOutcome.INCOMPLETE:
            labels.append("incomplete-review")

        if outcome == ReviewOutcome.TOTAL_FAILURE:
            labels.append("failed_review")

        if any(comment.type == ReviewType.SECURITY for comment in result.comments):
            labels.append("security-concern")

        if pull_request.changed_files > self.large_pr_threshold:
            labels.append("large-pr")

        if any(comment.type == ReviewType.DOCUMENTATION for comment in result.comments):
            labels.append("documentation-needed")

        if labels:
            pull_request.set_labels(*labels)

    def submit_review(self, pull_request: PullRequest, result: ReviewResult) -> None:
        self._dismiss_previous_reviews(pull_request)

        outcome = self._determine_review_outcome(result)

        try:
            if outcome == ReviewOutcome.APPROVED:
                pull_request.create_review(
                    body=(
                        "PRLens approved this pull request.\n\n"
                        "✅ Overall code quality meets expectations.\n"
                        "No critical issues were detected."
                    ),
                    event="APPROVE",
                )

            elif outcome == ReviewOutcome.CHANGES_REQUESTED:
                pull_request.create_review(
                    body=(
                        "PRLens requests changes on this pull request.\n\n"
                        "⚠️ Critical issues or significant quality concerns "
                        "were detected.\n"
                        "Please address the review findings before merging."
                    ),
                    event="REQUEST_CHANGES",
                )

            elif outcome == ReviewOutcome.INCOMPLETE:
                failed_list = ", ".join(result.failed_files)
                pull_request.create_review(
                    body=(
                        "PRLens could not complete the analysis for this pull request.\n\n"
                        "🟣 The following files failed to be analyzed and were not reviewed:\n"
                        f"{failed_list}\n\n"
                        "Please review these files manually, or re-run the workflow."
                    ),
                    event="COMMENT",
                )

            elif outcome == ReviewOutcome.TOTAL_FAILURE:
                pull_request.create_review(
                    body=(
                        "PRLens failed to complete the analysis for this pull request.\n\n"            
                        "⛔ All files failed to be analyzed. This may indicate a rate limit, "            
                        "API outage, or configuration issue.\n"            
                        "Please re-run the workflow or check the action logs."
                    ),
                    event="COMMENT",
                )

            elif outcome == ReviewOutcome.COMMENT and result.total_files == 0:
                pull_request.create_review(
                    body=(
                        "PRLens did not review any files in this pull request.\n\n"
                        "⚠️ None of the changed files match the configured target languages "
                        "or all files were excluded by your `.aireviewer.yml` rules.\n\n"
                        "To enable AI review, either:\n"
                        "- Add supported file types (`.py`, `.js`, `.ts`, `.java`) to your PR\n"
                        "- Update `target_languages` in `.aireviewer.yml`\n"
                        "- Review this pull request manually"
                    ),
                    event="COMMENT",
                )

            else:
                pull_request.create_review(
                    body=(
                        "PRLens completed its review.\n\n"
                        "ℹ️ No blocking issues were found, but there are "
                        "opportunities for improvement."
                    ),
                    event="COMMENT",
                )
        except GithubException as e:
            logger.warning("Failed to submit review: %s", e)

    def assign_reviewers(self, pull_request: PullRequest, result: ReviewResult, settings: Settings) -> None:
        if not result.has_critical_issues:
            return

        reviewers = {
            settings.reviewers_mapping.get(comment.type)
            for comment in result.comments
        }
        reviewers.discard(None)

        team_reviewers = []
        individual_reviewers = []

        for reviewer in reviewers:
            kind, name = _parse_reviewer(reviewer)
            if not name:
                continue
            if kind == "team":
                team_reviewers.append(name)
            elif name != pull_request.user.login:
                individual_reviewers.append(name)

        try:
            if individual_reviewers:
                pull_request.create_review_request(reviewers=individual_reviewers)
            if team_reviewers:
                pull_request.create_review_request(team_reviewers=team_reviewers)
        except GithubException as e:
            # A rejected request is only ever a warning, so a reviewer GitHub will
            # not accept is invisible unless the name is in the message.
            logger.warning(
                "Failed to assign reviewers %s / teams %s on %s: %s",
                individual_reviewers, team_reviewers, pull_request.html_url, e,
            )


def _parse_reviewer(raw: str) -> tuple[str, str]:
    """A configured reviewer -> ("user" | "team", name-as-GitHub-wants-it).

    The API takes a bare login ("octocat") and a bare team slug, but the value
    reaching here is typed by a human: the dashboard's own field invited an "@"
    and GitHub's UI shows handles that way, so "@octocat" is what actually gets
    stored — and it is rejected with a 422 that this module only logs. Strip the
    sigil rather than fail on it, and accept "org/team" alongside "team:slug",
    which is how a team is written everywhere else on GitHub.
    """
    name = raw.strip().lstrip("@")
    if not name:
        return "user", ""
    if name.startswith("team:"):
        return "team", name.removeprefix("team:").strip().lstrip("@")
    if "/" in name:
        return "team", name.rsplit("/", 1)[-1].strip()
    return "user", name