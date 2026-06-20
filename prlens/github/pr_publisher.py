from prlens.github.client import GitHubClient
from github.PullRequest import PullRequest
from prlens.models.review import ReviewType, ReviewResult


class PRPublisher:
    def __init__(self, client: GitHubClient):
        self.client = client

    def post_inline_comments(self, pull_request, comments):

    def post_summary(self, pull_request, result):

    def apply_labels(self, pull_request: PullRequest, result: ReviewResult) -> None:
        labels = []

        if result.score > 80 and not result.has_critical_issues:
            labels.append("ai-approved")

        if result.score < 50 or result.has_critical_issues:
            labels.append("needs-changes")

        if any(comment.type == ReviewType.SECURITY for comment in result.comments):
            labels.append("security-concern")

        if pull_request.changed_files > 20:
            labels.append("large-pr")

        if any(comment.type == ReviewType.DOCUMENTATION for comment in result.comments):
            labels.append("documentation-needed")

        pull_request.set_labels(*labels)

    def submit_review(self, pull_request: PullRequest, result: ReviewResult) -> None:
        if result.score > 80 and not result.has_critical_issues:
            pull_request.create_review(
                body=(
                    "PRLens approved this pull request.\n\n"
                    "✅ Overall code quality meets expectations.\n"
                    "No critical issues were detected."
                ),
                event="APPROVE"
            )

        elif result.score < 50 or result.has_critical_issues:
            pull_request.create_review(
                body=(
                    "PRLens requests changes on this pull request.\n\n"
                    "⚠️ Critical issues or significant quality concerns "
                    "were detected.\n"
                    "Please address the review findings before merging."
                ),
                event="REQUEST_CHANGES"
            )

        else:
            pull_request.create_review(
                body=(
                    "PRLens completed its review.\n\n"
                    "ℹ️ No blocking issues were found, but there are "
                    "opportunities for improvement."
                ),
                event="COMMENT"
            )

    def assign_reviewers(self, pull_request, settings):