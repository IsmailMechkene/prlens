from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv

import hmac
import hashlib
import os
import json
import time
import threading

load_dotenv()

from prlens.config.settings import load_settings
from prlens.core.agent import Agent
from prlens.github.client import GitHubClient
from prlens.github.pr_fetcher import PRFetcher
from prlens.github.pr_publisher import PRPublisher
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient

app = FastAPI()

_processing_lock = threading.Lock()
_processing_prs: set = set()
_last_processed: dict = {}
DEBOUNCE_SECONDS = 30

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def run_agent(repo_name: str, pr_number: int, actor: str) -> None:
    pr_key = f"{repo_name}#{pr_number}"
    now = time.time()

    with _processing_lock:
        # Reject if already running
        if pr_key in _processing_prs:
            print(f"Skipping: {pr_key} already processing")
            return

        # Reject if processed too recently
        last = _last_processed.get(pr_key, 0)
        if now - last < DEBOUNCE_SECONDS:
            print(f"Debouncing: {pr_key} processed {now - last:.1f}s ago")
            return

        # Mark as active
        _processing_prs.add(pr_key)
        _last_processed[pr_key] = now

    try:
        settings = load_settings()
        github_client = GitHubClient()
        llm_client = LLMClient(settings.llm_model)
        pr_fetcher = PRFetcher(github_client)
        analyzer = Analyzer(llm_client)
        pr_publisher = PRPublisher(github_client, settings)
        agent = Agent(llm_client, pr_fetcher, pr_publisher, analyzer, settings)
        agent.run(repo_name, pr_number, actor)
    finally:
        with _processing_lock:
            _processing_prs.discard(pr_key)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "PRLens"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature, secret):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)
    event_type = request.headers.get("X-GitHub-Event", "")

    if event_type != "pull_request":
        return {"status": "ignored", "reason": "not a pull_request event"}

    action = payload.get("action", "")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"action '{action}' not handled"}

    repo_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    actor = payload["pull_request"]["user"]["login"]

    background_tasks.add_task(run_agent, repo_name, pr_number, actor)
    return {"status": "accepted"}