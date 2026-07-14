"""Shared pytest fixtures for the PRLens test suite.

Everything here is mock/boilerplate only — no test cases live in this file.
All mocking is done with ``unittest.mock.MagicMock``. Fixtures are intentionally
configured with sensible, overridable defaults so individual tests only need to
tweak the pieces they care about.
"""

#pytest tests/ -v
#Test the coverage
#pip install pytest-cov
#pytest tests/ --cov=prlens --cov-report=term-missing

import json
from unittest.mock import MagicMock

import pytest
from github.PullRequest import PullRequest

from prlens.config.settings import Settings
from prlens.github.client import GitHubClient
from prlens.llm.client import LLMClient
from prlens.models.pr import (
    PR,
    FileChange,
    FileChangeStatus,
    PRStatus,
)

# ---------------------------------------------------------------------------
# LLM fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_llm_response() -> str:
    """A well-formed JSON string matching the ``FileReviewResponse`` schema.

    Use this as the default return value of ``LLMClient.generate`` so the
    analyzer parses a valid, non-empty response. Tests that need a different
    payload can build their own JSON string.
    """
    return json.dumps(
        {
            "comments": [
                {
                    "file_path": "example.py",
                    "line": 1,
                    "type": "security",
                    "severity": "critical",
                    "message": "Hardcoded secret detected.",
                    "suggestion": "Load the secret from an environment variable.",
                }
            ],
            "positives": ["Clear function naming."],
            "recommendations": ["Add input validation at the boundaries."],
        }
    )


@pytest.fixture
def mock_llm_client(valid_llm_response) -> MagicMock:
    """A mocked ``LLMClient``.

    ``generate`` returns a valid JSON response by default; override
    ``mock_llm_client.generate.return_value`` (or ``.side_effect``) per test.
    """
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    client.generate.return_value = valid_llm_response
    return client


# ---------------------------------------------------------------------------
# GitHub client / repository fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repo() -> MagicMock:
    """A mocked PyGithub ``Repository`` returned by ``GitHubClient.get_repo``."""
    repo = MagicMock(name="Repository")
    return repo


@pytest.fixture
def mock_github_client(mock_repo, mock_pull_request) -> MagicMock:
    """A mocked ``GitHubClient``.

    Wired so ``get_repo(...).get_pull(...)`` resolves to ``mock_pull_request``,
    mirroring the real ``PRFetcher.fetch_raw`` call chain.
    """
    client = MagicMock(spec=GitHubClient)
    client.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pull_request
    # Who PRLens posts as. The publisher recognises its own comments by this, so a
    # MagicMock here would make every "is this ours?" check meaningless.
    client.get_authenticated_login.return_value = "prlens[bot]"
    return client


# ---------------------------------------------------------------------------
# PyGithub PullRequest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_commit() -> MagicMock:
    """A mocked commit object (as returned by ``get_commits().reversed[0]``)."""
    return MagicMock(name="Commit")


@pytest.fixture
def mock_pull_request(mock_commit) -> MagicMock:
    """A mocked PyGithub ``PullRequest`` with realistic default attributes.

    Spec'd against the real ``PullRequest`` class so only genuine attributes and
    methods are allowed. Nested accessors used across the codebase
    (``user.login``, ``head.ref``, ``get_commits().reversed[0]``,
    ``get_review_requests()[0]`` ...) are pre-configured with harmless defaults.
    Override individual pieces in each test as needed.
    """
    pr = MagicMock(spec=PullRequest)

    # Scalar attributes
    pr.title = "Test PR"
    pr.body = "A test pull request."
    pr.number = 1
    pr.state = "open"
    pr.merged = False
    pr.changed_files = 1

    # Nested objects
    pr.user.login = "test-author"
    pr.head.ref = "feature-branch"
    pr.base.ref = "main"
    pr.labels = []

    # Paginated / iterable returns default to empty
    pr.get_files.return_value = []
    pr.get_issue_comments.return_value = []
    pr.get_review_comments.return_value = []
    pr.get_reviews.return_value = []
    # get_review_requests() -> (individual_reviewers, team_reviewers)
    pr.get_review_requests.return_value = ([], [])

    # get_commits().reversed[0] -> latest commit
    pr.get_commits.return_value.reversed.__getitem__.return_value = mock_commit

    return pr


# ---------------------------------------------------------------------------
# Settings / domain-model fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings() -> Settings:
    """Default ``Settings`` instance (real pydantic model, not a mock)."""
    return Settings()


@pytest.fixture
def sample_file_change() -> FileChange:
    """A single ``FileChange`` for a Python file with a small diff."""
    return FileChange(
        filename="example.py",
        status=FileChangeStatus.ADDED,
        additions=3,
        deletions=0,
        changes=3,
        patch='@@ -0,0 +1,3 @@\n+API_KEY = "sk-hardcoded"\n+def f():\n+    pass',
    )


@pytest.fixture
def sample_pr(sample_file_change) -> PR:
    """A domain ``PR`` model containing one changed file."""
    return PR(
        title="Test PR",
        author="test-author",
        body="A test pull request.",
        number=1,
        repo="test-owner/test-repo",
        status=PRStatus.OPEN,
        source_branch="feature-branch",
        target_branch="main",
        labels=[],
        reviewers=[],
        files=[sample_file_change],
    )
