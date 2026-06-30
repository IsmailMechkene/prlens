from collections import Counter
from enum import Enum

from github.PullRequest import PullRequest

from prlens.config.settings import Settings
from prlens.github.client import GitHubClient
from prlens.models.review import (
    ReviewComment,
    ReviewResult,
    ReviewType,
    Severity,
)


class ReviewOutcome(Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    COMMENT = "comment"
    INCOMPLETE = "incomplete"

class PRPublisher:
    SUMMARY_MARKER = "<!-- prlens-summary -->"

    SEVERITY_EMOJI = {
        Severity.INFO: "🔵",
        Severity.WARNING: "🟡",
        Severity.ERROR: "🟠",
        Severity.CRITICAL: "🔴",
    }

    def __init__(self, client: GitHubClient):
        self.client = client

    @staticmethod
    def _determine_review_outcome(result: ReviewResult) -> ReviewOutcome:
        if result.failed_files:
            return ReviewOutcome.INCOMPLETE

        if result.score > 80 and not result.has_critical_issues:
            return ReviewOutcome.APPROVED

        if result.score < 50 or result.has_critical_issues:
            return ReviewOutcome.CHANGES_REQUESTED

        return ReviewOutcome.COMMENT

    @staticmethod
    def _determine_review_status(result: ReviewResult) -> str:
        outcome = PRPublisher._determine_review_outcome(result)

        if outcome == ReviewOutcome.APPROVED:
            return "✅ Approved"

        if outcome == ReviewOutcome.CHANGES_REQUESTED:
            return "⚠️ Changes Requested"

        if outcome == ReviewOutcome.INCOMPLETE:
            return "🟣 Review Incomplete"

        return "ℹ️ Reviewed"

    def _build_summary(self, result: ReviewResult) -> str:
        badge = self._determine_review_status(result)

        outcome = self._determine_review_outcome(result)
        score_text = "N/A" if outcome == ReviewOutcome.INCOMPLETE else f"{result.score}/100"

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

    def _delete_previous_inline_comments(self, pull_request: PullRequest, authenticated_user: str) -> None:
        for comment in pull_request.get_review_comments():
            if comment.user.login in ("github-actions[bot]", authenticated_user):
                comment.delete()

    def _dismiss_previous_reviews(self, pull_request: PullRequest, authenticated_user: str) -> None:
        for review in pull_request.get_reviews():
            if review.user.login in ("github-actions[bot]", authenticated_user) and review.state in (
            "APPROVED", "CHANGES_REQUESTED"):
                review.dismiss(message="Superseded by a new PRLens review.")

    def post_inline_comments(self, pull_request: PullRequest, comments: list[ReviewComment], authenticated_user: str) -> None:
        self._delete_previous_inline_comments(pull_request, authenticated_user)

        commit = list(pull_request.get_commits())[-1]

        for comment in comments:
            emoji = self.SEVERITY_EMOJI.get(comment.severity, "⚪")

            body = f"{emoji} {comment.message}"

            if comment.suggestion:
                body += f"\n\n💡 **Suggestion:** {comment.suggestion}"

            if comment.line is None:
                pull_request.create_issue_comment(body=body)
            else:
                pull_request.create_review_comment(
                    body=body,
                    commit=commit,
                    path=comment.file_path,
                    line=comment.line,
                )

    def post_summary(self, pull_request: PullRequest, result: ReviewResult) -> None:
        summary = f"{self.SUMMARY_MARKER}\n{self._build_summary(result)}"

        for comment in pull_request.get_issue_comments():
            if self.SUMMARY_MARKER in (comment.body or ""):
                comment.edit(body=summary)
                return

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

        if any(comment.type == ReviewType.SECURITY for comment in result.comments):
            labels.append("security-concern")

        if pull_request.changed_files > 20:
            labels.append("large-pr")

        if any(comment.type == ReviewType.DOCUMENTATION for comment in result.comments):
            labels.append("documentation-needed")

        if labels:
            pull_request.set_labels(*labels)

    def submit_review(self, pull_request: PullRequest, result: ReviewResult, authenticated_user: str) -> None:
        self._dismiss_previous_reviews(pull_request, authenticated_user)

        outcome = self._determine_review_outcome(result)

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

        else:
            pull_request.create_review(
                body=(
                    "PRLens completed its review.\n\n"
                    "ℹ️ No blocking issues were found, but there are "
                    "opportunities for improvement."
                ),
                event="COMMENT",
            )

    def assign_reviewers(self, pull_request: PullRequest, result: ReviewResult, settings: Settings) -> None:
        if not result.has_critical_issues:
            return

        reviewers = {
            settings.reviewers_mapping.get(comment.type.value)
            for comment in result.comments
        }

        reviewers.discard(None)

        if reviewers:
            pull_request.create_review_request(reviewers=list(reviewers))