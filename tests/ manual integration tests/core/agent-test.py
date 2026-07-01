from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.client import LLMClient
from prlens.llm.analyzer import Analyzer
from prlens.core.agent import Agent

github_client = GitHubClient()
llm_client = LLMClient()
pr_fetcher = PRFetcher(github_client)
analyzer = Analyzer(llm_client)
pr_publisher = PRPublisher(github_client)

agent = Agent(llm_client, pr_fetcher, pr_publisher, analyzer)
agent.run("IsmailMechkene/ai-pr-reviewer-test", 4, "IsmailMechkene")