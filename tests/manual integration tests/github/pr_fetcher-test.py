from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher

client = GitHubClient()
fetcher = PRFetcher(client)
pr = fetcher.fetch("IsmailMechkene/ai-pr-reviewer-test", 1)
print(pr.model_dump_json(indent=2))