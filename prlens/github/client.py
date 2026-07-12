import base64
import binascii
import logging
import os
import time
from pathlib import Path

import jwt
import requests
from dotenv import load_dotenv
from github import Github, GithubException, Repository

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


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

    def _load_private_key(self) -> str:
        """The GitHub App private key, from whichever source is available.

        Three sources, in order: a .pem on disk, the key itself, or the key base64
        encoded. All three are tried rather than the first that is *configured*,
        because `*.pem` is both git- and docker-ignored — the key file does not exist
        in a deployed image. A GITHUB_APP_PRIVATE_KEY_PATH left over from a local
        checkout must therefore fall through to the environment instead of failing
        the whole process with a FileNotFoundError.
        """
        key_path_str = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        if key_path_str:
            key_path = Path(key_path_str)
            if not key_path.is_absolute():
                key_path = PROJECT_ROOT / key_path
            try:
                with open(key_path, "r") as f:
                    return f.read()
            except OSError:
                logger.warning(
                    "GITHUB_APP_PRIVATE_KEY_PATH points at %s, which cannot be read; "
                    "falling back to the key in the environment",
                    key_path,
                )

        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        if private_key:
            # A PEM pasted into a dashboard env var often arrives with its newlines
            # escaped, which RS256 signing rejects as a malformed key.
            return private_key.replace("\\n", "\n")

        private_key_b64 = os.getenv("GITHUB_APP_PRIVATE_KEY_B64")
        if private_key_b64:
            try:
                return base64.b64decode(private_key_b64).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as e:
                raise ValueError("GITHUB_APP_PRIVATE_KEY_B64 is not valid base64") from e

        raise ValueError(
            "Neither GITHUB_APP_PRIVATE_KEY_PATH (readable), GITHUB_APP_PRIVATE_KEY nor "
            "GITHUB_APP_PRIVATE_KEY_B64 yielded a private key. In a container the key "
            "file is not present, so set GITHUB_APP_PRIVATE_KEY_B64."
        )

    def _auth_as_github_app(self):
        private_key = getattr(self, '_private_key', None)
        app_id = getattr(self, '_app_id', None)
        installation_id = getattr(self, '_installation_id', None)

        if not private_key:
            private_key = self._load_private_key()

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


