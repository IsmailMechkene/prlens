import json
import os
import tempfile
import base64

from prlens.config.settings import load_settings
from prlens.core.agent import Agent
from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


if __name__ == "__main__":

    app_private_key_b64 = os.getenv("GITHUB_APP_PRIVATE_KEY_B64")
    if app_private_key_b64:
        private_key = base64.b64decode(app_private_key_b64).decode("utf-8")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(private_key)
            os.environ["GITHUB_APP_PRIVATE_KEY_PATH"] = f.name

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
    pr_publisher = PRPublisher(github_client, settings)

    agent = Agent(
        llm_client,
        pr_fetcher,
        pr_publisher,
        analyzer,
        settings,
    )

    agent.run(repo_name, pr_number, actor)