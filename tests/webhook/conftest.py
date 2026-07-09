"""Keep the webhook unit tests off any real database.

``run_agent`` now reads the repo's ``Installation`` row before reviewing, so that
a connected repo is reviewed with the settings edited in the dashboard. Without
this fixture the suite would open a connection to whatever ``DATABASE_URL`` points
at — for this project, a live Postgres.

Unsetting it makes ``_repo_config`` return ``None`` immediately, so ``run_agent``
falls back to ``load_settings()`` exactly as it did before. No existing assertion
changes; the tests simply stop reaching the network.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
