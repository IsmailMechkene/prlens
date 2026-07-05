from dataclasses import dataclass, field

from prlens.llm.analyzer import Analyzer
from prlens.models.pr import FileChange, FileChangeStatus
from prlens.models.review import ReviewType, Severity

@dataclass
class EvalCase:
    name: str                           # "hardcoded_api_key"
    patch: str                          # the diff content
    filename: str                       # "test.py"
    expected_types: list[ReviewType]    # [ReviewType.SECURITY]
    expected_min_severity: Severity     # Severity.CRITICAL
    should_have_comments: bool = True   # False for clean code cases


@dataclass
class EvalResult:
    case: EvalCase
    comments_found: list        # actual ReviewComment objects returned
    passed: bool                # did it meet expectations?
    reason: str                 # why it passed or failed



SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
    Severity.CRITICAL: 3,
}


def run_eval_case(case: EvalCase, analyzer: Analyzer) -> EvalResult:
    file = FileChange(
        filename=case.filename,
        status=FileChangeStatus.MODIFIED,
        additions=len(case.patch.splitlines()),
        deletions=0,
        changes=len(case.patch.splitlines()),
        patch=case.patch
    )

    response = analyzer.analyze_file(file)
    comments = response.comments

    if not case.should_have_comments:
        # clean code case
        passed = len(comments) == 0
        reason = "No comments found as expected" if passed else f"Unexpected {len(comments)} comment(s) found"
        return EvalResult(case=case, comments_found=comments, passed=passed, reason=reason)

    # expects comments
    if not comments:
        return EvalResult(case=case, comments_found=[], passed=False, reason="No comments found — false negative")

    # check if any comment matches expected type and severity
    matching = [
        c for c in comments
        if c.type in case.expected_types
           and SEVERITY_RANK[c.severity] >= SEVERITY_RANK[case.expected_min_severity]
    ]

    passed = len(matching) > 0
    reason = f"Found {len(matching)} matching comment(s)" if passed else "No comments matched expected type/severity"
    return EvalResult(case=case, comments_found=comments, passed=passed, reason=reason)


