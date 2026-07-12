import json

import pytest

from prlens.llm.analyzer import Analyzer
from prlens.models.review import ReviewResult, ReviewType, Severity


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

# ---------------------------------------------------------------------------
# Tolerating what the model actually returns
#
# The LLM is asked for an exact schema and mostly obeys, but a single stray value
# used to be fatal: FileReviewResponse was validated in one go, so one malformed
# comment discarded the file's other comments, its positives and its
# recommendations, and marked the file failed — which drags the PR towards
# TOTAL_FAILURE and inflates the score, because the findings that would have
# lowered it are gone.
# ---------------------------------------------------------------------------

def _response(**payload) -> str:
    return json.dumps(payload)


def _comment(**overrides) -> dict:
    return {
        "file_path": "app.py",
        "line": 3,
        "type": "security",
        "severity": "critical",
        "message": "SQL injection",
        "suggestion": "parameterise the query",
        **overrides,
    }


def test_parse_keeps_the_file_when_one_comment_is_malformed(mock_llm_client):
    """The production failure: `type: "error"` (a severity) on one of eight comments."""
    parsed = Analyzer(mock_llm_client)._parse_response(_response(
        comments=[_comment(line=i) for i in range(1, 8)] + [_comment(type="error")],
        positives=["good validation"],
        recommendations=["split this module"],
    ))

    assert len(parsed.comments) == 8  # nothing thrown away
    assert parsed.positives == ["good validation"]
    assert parsed.recommendations == ["split this module"]

    salvaged = parsed.comments[-1]
    assert salvaged.type is ReviewType.QUALITY  # "error" is a severity, mapped to a type
    assert salvaged.message == "SQL injection"  # the finding itself survives


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("type", "error", ReviewType.QUALITY),        # severity leaking into type
        ("type", "bug", ReviewType.QUALITY),
        ("type", "perf", ReviewType.PERFORMANCE),
        ("type", "vulnerability", ReviewType.SECURITY),
        ("type", "readability", ReviewType.STYLE),
        ("type", "docs", ReviewType.DOCUMENTATION),
        ("type", "something-invented", ReviewType.QUALITY),   # unknown -> fallback
        ("severity", "high", Severity.ERROR),
        ("severity", "blocker", Severity.CRITICAL),
        ("severity", "minor", Severity.INFO),
        ("severity", "something-invented", Severity.WARNING),  # unknown -> fallback
    ],
)
def test_near_miss_enum_values_are_mapped_not_dropped(mock_llm_client, field, value, expected):
    parsed = Analyzer(mock_llm_client)._parse_response(
        _response(comments=[_comment(**{field: value})])
    )

    assert getattr(parsed.comments[0], field) is expected


def test_line_accepts_a_range_or_a_prefix(mock_llm_client):
    parsed = Analyzer(mock_llm_client)._parse_response(_response(
        comments=[_comment(line="12-15"), _comment(line="L7"), _comment(line=None)],
    ))

    assert [c.line for c in parsed.comments] == [12, 7, None]


def test_an_extra_key_does_not_discard_the_file(mock_llm_client):
    parsed = Analyzer(mock_llm_client)._parse_response(_response(
        comments=[_comment()],
        positives=[],
        recommendations=[],
        summary="a field the model invented",
    ))

    assert len(parsed.comments) == 1


def test_an_irreparable_comment_is_dropped_and_the_rest_kept(mock_llm_client):
    no_message = _comment()
    del no_message["message"]

    parsed = Analyzer(mock_llm_client)._parse_response(_response(
        comments=[no_message, _comment(message="kept")],
    ))

    assert [c.message for c in parsed.comments] == ["kept"]


def test_a_json_array_is_still_a_failure(mock_llm_client):
    """Salvaging comments must not turn a wholly wrong response into a silent pass."""
    with pytest.raises(TypeError):
        Analyzer(mock_llm_client)._parse_response('["not", "an", "object"]')
