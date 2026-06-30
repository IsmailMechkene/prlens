import json

from prlens.llm.client import LLMClient
from prlens.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from prlens.models.pr import PR, FileChange
from prlens.models.review import ReviewComment, ReviewResult, Severity, FileReviewResponse
from prlens.config.settings import Settings, filter_files

from concurrent.futures import ThreadPoolExecutor


class Analyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze_file(self, file: FileChange) -> FileReviewResponse:
        full_prompt = f"{SYSTEM_PROMPT}\n\n{build_user_prompt(file)}"
        response = self.llm.generate(full_prompt)

        return self._parse_response(response)

    def analyze_pr(self, pr: PR, settings: Settings) -> ReviewResult:
        filtered_files = filter_files(pr.files, settings)
        all_comments = []
        all_positives = []
        all_recommendations = []
        failed_files = []

        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            futures = {executor.submit(self.analyze_file, file): file for file in filtered_files}

            for future in futures:
                file = futures[future]
                try:
                    analyzed_file = future.result()
                    all_comments.extend(analyzed_file.comments)
                    all_positives.extend(analyzed_file.positives)
                    all_recommendations.extend(analyzed_file.recommendations)
                except Exception as e:
                    failed_files.append(file.filename)
                    print(f"Warning: failed to analyze {file.filename}: {e}")

        score = self._calculate_score(all_comments)

        has_critical_issues = self._calculate_has_critical_issues(all_comments)

        return ReviewResult(
            score = score,
            comments = all_comments,
            positives = all_positives,
            recommendations = all_recommendations,
            has_critical_issues = has_critical_issues,
            failed_files = failed_files
        )

    def _parse_response(self, response: str) -> FileReviewResponse:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            response = response.replace("json", "", 1)

        data = json.loads(response)
        return FileReviewResponse(**data)

    def _calculate_score(self, comments: list[ReviewComment]) -> int:
        PENALTIES = {
            Severity.INFO: 1,
            Severity.WARNING: 4,
            Severity.ERROR: 10,
            Severity.CRITICAL: 25,
        }

        score = 100 - sum(
            PENALTIES.get(comment.severity, 0)
            for comment in comments
        )

        return max(0, score)

    def _calculate_has_critical_issues(self, comments: list[ReviewComment]) -> bool:
        return any(comment.severity == Severity.CRITICAL for comment in comments)

