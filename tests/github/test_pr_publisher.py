from unittest.mock import MagicMock

import pytest
from github import GithubException

from prlens.config.settings import Settings
from prlens.github.pr_publisher import PRPublisher
from prlens.models.review import ReviewComment, ReviewResult, ReviewType, Severity


def test_apply_labels_approved(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(score=90, total_files=1, positives=["Clean code."])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    mock_pull_request.set_labels.assert_called_once()
    call_args = mock_pull_request.set_labels.call_args[0]

    assert "ai-approved" in call_args


def test_apply_labels_needs_changes(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(
        score=30,
        total_files=1,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.QUALITY,
            severity=Severity.ERROR,
            message="Poor code quality.",
        )]
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    mock_pull_request.set_labels.assert_called_once()
    call_args = mock_pull_request.set_labels.call_args[0]

    assert "needs-changes" in call_args


def test_apply_labels_security_concern(mock_github_client, mock_pull_request, settings):
    security_comment = ReviewComment(
        file_path="example.py",
        type=ReviewType.SECURITY,
        severity=Severity.CRITICAL,
        message="Hardcoded secret detected.",
    )
    result = ReviewResult(score=50, total_files=1, comments=[security_comment])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    mock_pull_request.set_labels.assert_called_once()
    call_args = mock_pull_request.set_labels.call_args[0]

    assert "security-concern" in call_args


def test_post_summary_creates_comment(mock_pull_request, mock_github_client, settings):
    result = ReviewResult(score=90, total_files=1)

    publisher = PRPublisher(mock_github_client, settings)
    publisher.post_summary(mock_pull_request, result)

    mock_pull_request.create_issue_comment.assert_called_once()


def test_submit_review_approves(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(score=90, total_files=1, positives=["Clean code."])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.submit_review(mock_pull_request, result, "test-user")

    mock_pull_request.create_review.assert_called_once()
    call_args = mock_pull_request.create_review.call_args[1]
    assert call_args["event"] == "APPROVE"


def test_apply_labels_incomplete_review(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(score=70, total_files=2, failed_files=["broken.py"])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    call_args = mock_pull_request.set_labels.call_args[0]
    assert "incomplete-review" in call_args


def test_apply_labels_failed_review(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(score=0, total_files=1, failed_files=["broken.py"])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    call_args = mock_pull_request.set_labels.call_args[0]
    assert "failed_review" in call_args


def test_apply_labels_large_pr(mock_github_client, mock_pull_request, settings):
    mock_pull_request.changed_files = 25
    result = ReviewResult(score=90, total_files=1, positives=["Clean code."])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    call_args = mock_pull_request.set_labels.call_args[0]
    assert "large-pr" in call_args


def test_apply_labels_documentation_needed(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(
        score=70,
        total_files=1,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.DOCUMENTATION,
            severity=Severity.INFO,
            message="Missing docstring.",
        )],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.apply_labels(mock_pull_request, result)

    call_args = mock_pull_request.set_labels.call_args[0]
    assert "documentation-needed" in call_args


def test_build_summary_status_badges(mock_github_client, settings):
    publisher = PRPublisher(mock_github_client, settings)

    approved = ReviewResult(score=90, total_files=1, positives=["Clean code."])
    assert "✅ Approved" in publisher._build_summary(approved)

    changes = ReviewResult(
        score=30,
        total_files=1,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.QUALITY,
            severity=Severity.ERROR,
            message="Poor quality.",
        )],
    )
    assert "⚠️ Changes Requested" in publisher._build_summary(changes)

    incomplete = ReviewResult(score=70, total_files=2, failed_files=["broken.py"])
    assert "🟣 Review Incomplete" in publisher._build_summary(incomplete)

    total_failure = ReviewResult(score=0, total_files=1, failed_files=["broken.py"])
    assert "⛔ Failed Review" in publisher._build_summary(total_failure)


def test_post_summary_deletes_existing_marker(mock_github_client, mock_pull_request, settings):
    existing = MagicMock()
    existing.body = f"{PRPublisher.SUMMARY_MARKER}\nold summary"
    mock_pull_request.get_issue_comments.return_value = [existing]

    result = ReviewResult(score=90, total_files=1, positives=["Clean code."])

    publisher = PRPublisher(mock_github_client, settings)
    publisher.post_summary(mock_pull_request, result)

    existing.delete.assert_called_once()
    mock_pull_request.create_issue_comment.assert_called_once()


def test_post_inline_comments_issue_comment_for_none_line(mock_github_client, mock_pull_request, settings):
    comments = [ReviewComment(
        file_path="example.py",
        line=None,
        type=ReviewType.QUALITY,
        severity=Severity.INFO,
        message="General note.",
    )]

    publisher = PRPublisher(mock_github_client, settings)
    publisher.post_inline_comments(mock_pull_request, comments, "test-user")

    mock_pull_request.create_issue_comment.assert_called_once()
    mock_pull_request.create_review_comment.assert_not_called()


def test_submit_review_requests_changes(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(
        score=30,
        total_files=1,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.QUALITY,
            severity=Severity.ERROR,
            message="Poor code quality.",
        )],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.submit_review(mock_pull_request, result, "test-user")

    call_args = mock_pull_request.create_review.call_args[1]
    assert call_args["event"] == "REQUEST_CHANGES"


def test_submit_review_incomplete(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(
        score=70,
        total_files=2,
        failed_files=["broken.py"],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.submit_review(mock_pull_request, result, "test-user")

    call_args = mock_pull_request.create_review.call_args[1]
    assert call_args["event"] == "COMMENT"
    assert "broken.py" in call_args["body"]


def test_submit_review_total_failure(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(
        score=0,
        total_files=1,
        failed_files=["broken.py"],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.submit_review(mock_pull_request, result, "test-user")

    call_args = mock_pull_request.create_review.call_args[1]
    assert call_args["event"] == "COMMENT"
    assert "All files failed" in call_args["body"]


def test_submit_review_comment_no_files(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(score=70, total_files=0)

    publisher = PRPublisher(mock_github_client, settings)
    publisher.submit_review(mock_pull_request, result, "test-user")

    call_args = mock_pull_request.create_review.call_args[1]
    assert call_args["event"] == "COMMENT"
    assert "did not review any files" in call_args["body"]


def test_submit_review_comment_default(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(
        score=60,
        total_files=1,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.STYLE,
            severity=Severity.INFO,
            message="Minor style nit.",
        )],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.submit_review(mock_pull_request, result, "test-user")

    call_args = mock_pull_request.create_review.call_args[1]
    assert call_args["event"] == "COMMENT"
    assert "completed its review" in call_args["body"]


def test_submit_review_handles_github_exception(mock_github_client, mock_pull_request, settings):
    result = ReviewResult(score=90, total_files=1, positives=["Clean code."])
    mock_pull_request.create_review.side_effect = GithubException(
        422, {"message": "Unprocessable"}, {}
    )

    publisher = PRPublisher(mock_github_client, settings)
    # Should swallow the exception and not raise.
    publisher.submit_review(mock_pull_request, result, "test-user")

    mock_pull_request.create_review.assert_called_once()


def test_dismiss_previous_reviews(mock_github_client, mock_pull_request, settings):
    matching = MagicMock()
    matching.user.login = "github-actions[bot]"
    matching.state = "APPROVED"

    other = MagicMock()
    other.user.login = "someone-else"
    other.state = "APPROVED"

    mock_pull_request.get_reviews.return_value = [matching, other]

    publisher = PRPublisher(mock_github_client, settings)
    publisher._dismiss_previous_reviews(mock_pull_request, "test-user")

    matching.dismiss.assert_called_once()
    other.dismiss.assert_not_called()


def test_delete_previous_inline_comments(mock_github_client, mock_pull_request, settings):
    mine = MagicMock()
    mine.user.login = "test-user"

    theirs = MagicMock()
    theirs.user.login = "someone-else"

    mock_pull_request.get_review_comments.return_value = [mine, theirs]

    publisher = PRPublisher(mock_github_client, settings)
    publisher._delete_previous_inline_comments(mock_pull_request, "test-user")

    mine.delete.assert_called_once()
    theirs.delete.assert_not_called()


def test_post_inline_comments_falls_back_to_issue_comment(mock_github_client, mock_pull_request, settings):
    comments = [ReviewComment(
        file_path="example.py",
        line=5,
        type=ReviewType.QUALITY,
        severity=Severity.WARNING,
        message="Consider refactoring.",
        suggestion="Extract a helper.",
    )]
    mock_pull_request.create_review_comment.side_effect = GithubException(
        422, {"message": "line not in diff"}, {}
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.post_inline_comments(mock_pull_request, comments, "test-user")

    mock_pull_request.create_review_comment.assert_called_once()
    mock_pull_request.create_issue_comment.assert_called_once()


def test_assign_reviewers_no_critical_returns_early(mock_github_client, mock_pull_request):
    settings = Settings(reviewers_mapping={ReviewType.SECURITY: "alice"})
    result = ReviewResult(score=90, total_files=1, has_critical_issues=False)

    publisher = PRPublisher(mock_github_client, settings)
    publisher.assign_reviewers(mock_pull_request, result, settings)

    mock_pull_request.create_review_request.assert_not_called()


def test_assign_reviewers_individual(mock_github_client, mock_pull_request):
    settings = Settings(reviewers_mapping={ReviewType.SECURITY: "alice"})
    result = ReviewResult(
        score=40,
        total_files=1,
        has_critical_issues=True,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.SECURITY,
            severity=Severity.CRITICAL,
            message="Hardcoded secret.",
        )],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.assign_reviewers(mock_pull_request, result, settings)

    mock_pull_request.create_review_request.assert_called_once_with(reviewers=["alice"])


def test_assign_reviewers_team(mock_github_client, mock_pull_request):
    settings = Settings(reviewers_mapping={ReviewType.SECURITY: "team:sec-team"})
    result = ReviewResult(
        score=40,
        total_files=1,
        has_critical_issues=True,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.SECURITY,
            severity=Severity.CRITICAL,
            message="Hardcoded secret.",
        )],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.assign_reviewers(mock_pull_request, result, settings)

    mock_pull_request.create_review_request.assert_called_once_with(team_reviewers=["sec-team"])


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        # The dashboard stores what the user typed, and a GitHub handle is written
        # with an "@" everywhere GitHub shows one. The API rejects it, so it is
        # stripped here rather than 422-ing into a warning nobody reads.
        ("@alice", {"reviewers": ["alice"]}),
        ("alice", {"reviewers": ["alice"]}),
        ("  alice  ", {"reviewers": ["alice"]}),
        ("team:sec-team", {"team_reviewers": ["sec-team"]}),
        ("@team:sec-team", {"team_reviewers": ["sec-team"]}),
        # "org/team" is how a team is written everywhere else on GitHub.
        ("@acme/appsec", {"team_reviewers": ["appsec"]}),
        ("acme/appsec", {"team_reviewers": ["appsec"]}),
    ],
)
def test_assign_reviewers_normalises_configured_name(
    mock_github_client, mock_pull_request, configured, expected
):
    settings = Settings(reviewers_mapping={ReviewType.SECURITY: configured})
    result = ReviewResult(
        score=40,
        total_files=1,
        has_critical_issues=True,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.SECURITY,
            severity=Severity.CRITICAL,
            message="Hardcoded secret.",
        )],
    )

    publisher = PRPublisher(mock_github_client, settings)
    publisher.assign_reviewers(mock_pull_request, result, settings)

    mock_pull_request.create_review_request.assert_called_once_with(**expected)


def test_assign_reviewers_handles_github_exception(mock_github_client, mock_pull_request):
    settings = Settings(reviewers_mapping={ReviewType.SECURITY: "alice"})
    result = ReviewResult(
        score=40,
        total_files=1,
        has_critical_issues=True,
        comments=[ReviewComment(
            file_path="example.py",
            type=ReviewType.SECURITY,
            severity=Severity.CRITICAL,
            message="Hardcoded secret.",
        )],
    )
    mock_pull_request.create_review_request.side_effect = GithubException(
        422, {"message": "Unprocessable"}, {}
    )

    publisher = PRPublisher(mock_github_client, settings)
    # Should swallow the exception and not raise.
    publisher.assign_reviewers(mock_pull_request, result, settings)

    mock_pull_request.create_review_request.assert_called_once()