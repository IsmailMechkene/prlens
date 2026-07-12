from unittest.mock import MagicMock

from prlens.core.agent import Agent


def test_run_executes_full_pipeline(settings):
    mock_fetcher = MagicMock()
    mock_analyzer = MagicMock()
    mock_publisher = MagicMock()
    mock_llm = MagicMock()

    agent = Agent(mock_llm, mock_fetcher, mock_publisher, mock_analyzer, settings)
    agent.run("owner/repo", 1, "test-user")

    mock_fetcher.fetch_raw.assert_called_once_with("owner/repo", 1)
    mock_fetcher.map_to_pr.assert_called_once()
    mock_analyzer.analyze_pr.assert_called_once()
    mock_publisher.post_summary.assert_called_once()
    mock_publisher.submit_review.assert_called_once()

