import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from prlens.webhook import app as webhook_app
from prlens.webhook.app import app, run_agent, verify_signature

client = TestClient(app)

SECRET = "test-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def _clear_dedup_state():
    """Reset the module-level debounce/in-flight state around every test."""
    webhook_app._processing_prs.clear()
    webhook_app._last_processed.clear()
    yield
    webhook_app._processing_prs.clear()
    webhook_app._last_processed.clear()


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------

def test_verify_signature_accepts_matching_signature():
    body = b'{"hello": "world"}'
    assert verify_signature(body, _sign(body), SECRET) is True


def test_verify_signature_rejects_wrong_signature():
    body = b'{"hello": "world"}'
    assert verify_signature(body, "sha256=deadbeef", SECRET) is False


# ---------------------------------------------------------------------------
# health check
# ---------------------------------------------------------------------------

def test_health_check():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "PRLens"}


# ---------------------------------------------------------------------------
# /webhook endpoint
# ---------------------------------------------------------------------------

def test_webhook_returns_500_when_secret_not_configured():
    with patch("prlens.webhook.app.os.getenv", return_value=""):
        resp = client.post(
            "/webhook",
            content=b"{}",
            headers={"X-Hub-Signature-256": "sha256=whatever"},
        )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Webhook secret not configured"


def test_webhook_rejects_invalid_signature():
    body = b'{"action": "opened"}'
    with patch("prlens.webhook.app.os.getenv", return_value=SECRET):
        resp = client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": "sha256=bad",
                "X-GitHub-Event": "pull_request",
            },
        )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Invalid signature"


def test_webhook_ignores_non_pull_request_event():
    body = json.dumps({"action": "opened"}).encode()
    with patch("prlens.webhook.app.os.getenv", return_value=SECRET):
        resp = client.post(
            "/webhook",
            content=body,
            headers={"X-Hub-Signature-256": _sign(body), "X-GitHub-Event": "push"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_ignores_unhandled_action():
    body = json.dumps({"action": "closed"}).encode()
    with patch("prlens.webhook.app.os.getenv", return_value=SECRET):
        resp = client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": _sign(body),
                "X-GitHub-Event": "pull_request",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert "closed" in resp.json()["reason"]


def test_webhook_accepts_and_schedules_review():
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/repo"},
        "pull_request": {"number": 7, "user": {"login": "alice"}},
    }
    body = json.dumps(payload).encode()
    with patch("prlens.webhook.app.os.getenv", return_value=SECRET), \
         patch("prlens.webhook.app.run_agent") as mock_run:
        resp = client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": _sign(body),
                "X-GitHub-Event": "pull_request",
            },
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}
    mock_run.assert_called_once_with("owner/repo", 7, "alice")


# ---------------------------------------------------------------------------
# run_agent (debounce / in-flight guards + pipeline wiring)
# ---------------------------------------------------------------------------

def _patch_pipeline():
    """Patch every collaborator run_agent builds so nothing real is invoked."""
    return [
        patch("prlens.webhook.app.load_settings"),
        patch("prlens.webhook.app.GitHubClient"),
        patch("prlens.webhook.app.LLMClient"),
        patch("prlens.webhook.app.PRFetcher"),
        patch("prlens.webhook.app.Analyzer"),
        patch("prlens.webhook.app.PRPublisher"),
    ]


def test_run_agent_runs_pipeline_and_clears_state():
    patches = _patch_pipeline()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
         patch("prlens.webhook.app.Agent") as mock_agent:
        run_agent("owner/repo", 1, "alice")

    mock_agent.return_value.run.assert_called_once_with("owner/repo", 1, "alice")
    # The finally block always removes the in-flight marker.
    assert "owner/repo#1" not in webhook_app._processing_prs
    # A successful run records the timestamp for debouncing.
    assert "owner/repo#1" in webhook_app._last_processed


def test_run_agent_skips_when_already_processing():
    webhook_app._processing_prs.add("owner/repo#2")
    with patch("prlens.webhook.app.Agent") as mock_agent:
        run_agent("owner/repo", 2, "bob")
    mock_agent.assert_not_called()


def test_run_agent_debounces_recently_processed_pr():
    webhook_app._last_processed["owner/repo#3"] = time.time()
    with patch("prlens.webhook.app.Agent") as mock_agent:
        run_agent("owner/repo", 3, "carol")
    mock_agent.assert_not_called()
