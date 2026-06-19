from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.llm.client import LLMClient
from prlens.llm.analyzer import Analyzer
from prlens.config.settings import load_settings

client = GitHubClient()
fetcher = PRFetcher(client)
pr = fetcher.fetch("IsmailMechkene/ai-pr-reviewer-test", 1)

llm = LLMClient()
analyzer = Analyzer(llm)
settings = load_settings()

result = analyzer.analyze_pr(pr, settings)
print(result.model_dump_json(indent=2))