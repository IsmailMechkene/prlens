import json
import os

from prlens.config.settings import load_settings
from prlens.core.agent import Agent
from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient

if __name__ == "__main__":
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        raise ValueError("GITHUB_EVENT_PATH not found")

    with open(event_path) as f:
        event_data = json.load(f)

    repo_name = os.getenv("GITHUB_REPOSITORY")
    if not repo_name:
        raise ValueError("GITHUB_REPOSITORY not found in environment")

    if "pull_request" not in event_data:
        raise ValueError("This workflow was not triggered by a pull_request event — skipping.")
    pr_number = event_data["pull_request"]["number"]

    actor = os.getenv("GITHUB_ACTOR", "local-test-user")

    settings = load_settings()

    github_client = GitHubClient()

    model = settings.llm_model
    llm_client = LLMClient(model)

    pr_fetcher = PRFetcher(github_client)
    analyzer = Analyzer(llm_client)
    pr_publisher = PRPublisher(github_client)

    agent = Agent(
        llm_client,
        pr_fetcher,
        pr_publisher,
        analyzer,
        settings,
    )

    agent.run(repo_name, pr_number, actor)