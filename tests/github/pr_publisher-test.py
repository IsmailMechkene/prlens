from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.llm.client import LLMClient
from prlens.llm.analyzer import Analyzer
from prlens.github.pr_publisher import PRPublisher
from prlens.config.settings import load_settings

client = GitHubClient()
fetcher = PRFetcher(client)
pr = fetcher.fetch("IsmailMechkene/ai-pr-reviewer-test", 4)

llm = LLMClient()
analyzer = Analyzer(llm)
settings = load_settings()
result = analyzer.analyze_pr(pr, settings)

publisher = PRPublisher(client)

repo = client.get_repo("IsmailMechkene/ai-pr-reviewer-test")
github_pr = repo.get_pull(4)

publisher.apply_labels(github_pr, result)
publisher.submit_review(github_pr, result)
publisher.post_inline_comments(github_pr, result.comments)
publisher.post_summary(github_pr, result)