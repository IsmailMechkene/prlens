from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from prlens.github.client import GitHubClient


def test_init_raises_without_token():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", return_value=None):
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            GitHubClient()


def test_init_creates_client_with_token():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", return_value="ghp_token"), \
         patch("prlens.github.client.Github") as mock_github:
        client = GitHubClient()

        assert client.token == "ghp_token"
        mock_github.assert_called_once_with("ghp_token")
        assert client.client == mock_github.return_value


def test_get_repo_returns_repository():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", return_value="ghp_token"), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

        repo = MagicMock(name="Repository")
        client.client.get_repo.return_value = repo

        result = client.get_repo("owner/repo")

        client.client.get_repo.assert_called_once_with("owner/repo")
        assert result == repo


def test_get_repo_raises_on_github_exception():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", return_value="ghp_token"), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

        client.client.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, {}
        )

        with pytest.raises(ValueError, match="Could not access repository"):
            client.get_repo("owner/missing")
