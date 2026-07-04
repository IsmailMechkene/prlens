from prlens.github.pr_publisher import PRPublisher
from prlens.models.review import ReviewResult, ReviewType, ReviewComment, Severity


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