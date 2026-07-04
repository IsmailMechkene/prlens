from prlens.github.pr_fetcher import PRFetcher
from prlens.models.pr import PR, PRStatus


def test_fetch_raw_calls_get_pull(mock_github_client, mock_pull_request):
    fetcher = PRFetcher(mock_github_client)
    result = fetcher.fetch_raw("owner/repo", 1)

    mock_github_client.get_repo.assert_called_once_with("owner/repo")
    assert result == mock_pull_request


def test_map_to_pr_returns_pr_model(mock_github_client, mock_pull_request):
    fetcher = PRFetcher(mock_github_client)
    result = fetcher.fetch_raw("owner/repo", 1)

    pr = fetcher.map_to_pr(result, "owner/repo")

    assert isinstance(pr, PR)


def test_map_to_pr_maps_author(mock_github_client, mock_pull_request):
    fetcher = PRFetcher(mock_github_client)
    result = fetcher.fetch_raw("owner/repo", 1)

    pr = fetcher.map_to_pr(result, "owner/repo")

    assert pr.author == mock_pull_request.user.login


def test_map_to_pr_handles_merged_status(mock_github_client, mock_pull_request):
    mock_pull_request.merged = True

    fetcher = PRFetcher(mock_github_client)
    result = fetcher.fetch_raw("owner/repo", 1)

    pr = fetcher.map_to_pr(result, "owner/repo")

    assert pr.status == PRStatus.MERGED