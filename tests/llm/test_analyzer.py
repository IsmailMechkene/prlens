from prlens.llm.analyzer import Analyzer
from prlens.models.review import ReviewResult


def test_analyze_pr_returns_review_result(mock_llm_client, sample_pr, settings):
    analyzer = Analyzer(mock_llm_client)
    result = analyzer.analyze_pr(sample_pr, settings)
    assert isinstance(result, ReviewResult)


def test_analyze_pr_detects_critical_issues(mock_llm_client, sample_pr, settings):
    analyzer = Analyzer(mock_llm_client)
    result = analyzer.analyze_pr(sample_pr, settings)
    assert result.has_critical_issues is True


def test_analyze_pr_calculates_score(mock_llm_client, sample_pr, settings):
    analyzer = Analyzer(mock_llm_client)
    result = analyzer.analyze_pr(sample_pr, settings)
    assert result.score == 75


def test_analyze_pr_tracks_failed_files(mock_llm_client, sample_pr, sample_file_change, settings):
    mock_llm_client.generate.side_effect = Exception("API error")

    analyzer = Analyzer(mock_llm_client)
    result = analyzer.analyze_pr(sample_pr, settings)

    assert sample_file_change.filename in result.failed_files