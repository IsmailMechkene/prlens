from prlens.config.settings import Settings
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient
from prlens.models.pr import PR
from prlens.models.review import ReviewResult


class Agent:
    def __init__(self, llm_client: LLMClient, pr_fetcher: PRFetcher, pr_publisher: PRPublisher, analyzer: Analyzer, settings: Settings):
        self.llm_client = llm_client
        self.pr_fetcher = pr_fetcher
        self.pr_publisher = pr_publisher
        self.analyzer = analyzer
        self.settings = settings

    def run(self, repo_name: str, pr_number: int, actor: str) -> tuple[PR, ReviewResult]:
        github_pr = self.pr_fetcher.fetch_raw(repo_name, pr_number)
        pr = self.pr_fetcher.map_to_pr(github_pr, repo_name)

        result = self.analyzer.analyze_pr(pr, self.settings)

        # `actor` is the PR's author and is deliberately not passed on: it used to be
        # handed to the publisher as the "authenticated user" whose comments may be
        # cleaned up on a re-review, which is a human, not PRLens. The publisher now
        # resolves its own identity from the GitHub client.
        self.pr_publisher.apply_labels(github_pr, result)
        self.pr_publisher.post_summary(github_pr, result)
        self.pr_publisher.post_inline_comments(github_pr, result.comments)
        self.pr_publisher.submit_review(github_pr, result)
        self.pr_publisher.assign_reviewers(github_pr, result, self.settings)

        return pr, result
