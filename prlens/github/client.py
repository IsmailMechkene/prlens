from github import Github, Repository, GithubException
from dotenv import load_dotenv
from pathlib import Path

import os
import jwt
import time
import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class GitHubClient:
    def __init__(self):
        load_dotenv()

        if os.getenv("GITHUB_APP_ID"):
            self._auth_as_github_app()
        else:
            self._auth_as_pat()

    def _auth_as_pat(self):
        self.token = os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment")

        self.client = Github(self.token)

    def _auth_as_github_app(self):
        private_key = getattr(self, '_private_key', None)
        app_id = getattr(self, '_app_id', None)
        installation_id = getattr(self, '_installation_id', None)

        if not private_key:
            key_path = PROJECT_ROOT / os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "prlens-reviewer.pem")
            if not key_path:
                raise ValueError("GITHUB_APP_PRIVATE_KEY_PATH not found in environment")
            with open(key_path, "r") as f:
                private_key = f.read()

        if not app_id:
            app_id = os.getenv("GITHUB_APP_ID")
            if not app_id:
                raise ValueError("GITHUB_APP_ID not found in environment")

        if not installation_id:
            installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
            if not installation_id:
                raise ValueError("GITHUB_APP_INSTALLATION_ID not found in environment")


        payload = {
            "iat": int(time.time()) - 60,         # issued at (60 seconds ago to allow clock drift)
            "exp": int(time.time()) + (10 * 60),  # expires in 10 minutes (GitHub's max)
            "iss": app_id,                        # issuer = your App ID
        }

        jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

        response = requests.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
            }
        )
        if response.status_code != 201:
            raise ValueError(f"Failed to get installation token: {response.json()}")

        installation_token = response.json()["token"]
        self.client = Github(installation_token)
        self._token_expiry = int(time.time()) + 3600
        self._installation_id = installation_id
        self._private_key = private_key
        self._app_id = app_id

    def _refresh_token_if_needed(self):
        if hasattr(self, '_token_expiry') and int(time.time()) > self._token_expiry - 300:
            #refresh 5 minutes before expiry rather than waiting until it's actually expired
            self._auth_as_github_app()


    def get_repo(self, repo_name: str) -> Repository.Repository:
        self._refresh_token_if_needed()
        try:
            repo = self.client.get_repo(repo_name)
        except GithubException as ge:
            raise ValueError(f"Could not access repository '{repo_name}': {ge}")
        return  repo


