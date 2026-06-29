from prlens.core.agent import Agent
from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient

import json
import os



event_path = os.getenv("GITHUB_EVENT_PATH")
with open(event_path) as f:
    event_data = json.load(f)

repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = event_data["pull_request"]["number"]

github_client = GitHubClient()
llm_client = LLMClient()
pr_fetcher = PRFetcher(github_client)
analyzer = Analyzer(llm_client)
pr_publisher = PRPublisher(github_client)

agent = Agent(llm_client, pr_fetcher, pr_publisher, analyzer)
agent.run(repo_name, pr_number)