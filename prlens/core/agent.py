from prlens.config.settings import load_settings
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient


class Agent:
    def __init__(self, llm_client: LLMClient, pr_fetcher: PRFetcher, pr_publisher: PRPublisher, analyzer: Analyzer):
        self.llm_client = llm_client
        self.pr_fetcher = pr_fetcher
        self.pr_publisher = pr_publisher
        self.analyzer = analyzer

    def run(self, repo_name: str, pr_number: int, actor: str) -> None:
        github_pr = self.pr_fetcher.fetch_raw(repo_name, pr_number)
        pr = self.pr_fetcher.map_to_pr(github_pr, repo_name)

        settings = load_settings()
        result = self.analyzer.analyze_pr(pr, settings)

        self.pr_publisher.apply_labels(github_pr, result)
        self.pr_publisher.submit_review(github_pr, result, actor)
        self.pr_publisher.post_inline_comments(github_pr, result.comments, actor)
        self.pr_publisher.post_summary(github_pr, result)
        self.pr_publisher.assign_reviewers(github_pr, result, settings)