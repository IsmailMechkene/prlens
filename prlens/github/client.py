import base64
import binascii
import logging
import os
import re
import time
from pathlib import Path

import jwt
import requests
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from dotenv import load_dotenv
from github import Github, GithubException, Repository

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)

_PEM_RE = re.compile(
    r"-{2,}\s*BEGIN\s+(?P<label>[A-Z0-9 ]+?)\s*-{2,}(?P<body>.*?)-{2,}\s*END\s+(?P=label)\s*-{2,}",
    re.DOTALL,
)


def _canonical_pem(raw: str) -> str:
    """Rebuild a PEM from a value that has been through an environment variable.

    A key pasted into a hosting dashboard rarely survives intact: the newlines come
    back as the two characters ``\\n``, or as spaces, or the whole thing arrives on
    one line, and the value may be wrapped in quotes. Every one of those parses as
    "not a key" to PyJWT, with no clue as to why. So rather than trust the text,
    take the base64 body out of it and re-emit a correct PEM: header, 64-character
    lines, footer, trailing newline. Already-correct keys pass through unchanged.
    """
    text = raw.strip()

    # A shell that quoted the value for you.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()

    # Not a PEM at all? Then it should be the base64 of one. The encodings are tried
    # in turn because a key base64'd through PowerShell comes out UTF-16, and one
    # written by a Windows editor carries a BOM — both decode to gibberish as UTF-8.
    if "BEGIN" not in text:
        try:
            decoded = base64.b64decode(text, validate=False)
        except (binascii.Error, ValueError):
            return raw  # let the caller's validation produce the error message

        for encoding in ("utf-8-sig", "utf-16", "utf-8"):
            try:
                text = decoded.decode(encoding).strip()
                break
            except UnicodeDecodeError:
                continue
        else:
            return raw

    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n")

    match = _PEM_RE.search(text)
    if not match:
        return text

    label = " ".join(match.group("label").split())
    body = re.sub(r"\s+", "", match.group("body"))
    lines = "\n".join(body[i:i + 64] for i in range(0, len(body), 64))
    return f"-----BEGIN {label}-----\n{lines}\n-----END {label}-----\n"


def _validated_pem(raw: str, source: str) -> str:
    """Canonicalise a private key and prove it parses, or say exactly what is wrong.

    ``source`` is the name of the variable it came from, so a bad key points at the
    thing to go and fix.
    """
    pem = _canonical_pem(raw)

    try:
        load_pem_private_key(pem.encode(), password=None)
    except (ValueError, TypeError, UnsupportedAlgorithm) as e:
        head = pem.strip().splitlines()[0][:40] if pem.strip() else "<empty>"
        raise ValueError(
            f"The GitHub App private key in {source} is not a usable private key "
            f"({e}). It starts with {head!r}. It must be the App's .pem — the whole "
            "file, including the BEGIN/END lines — or that file base64 encoded "
            "(base64 -w0 your-app.pem). A public key or a passphrase-protected key "
            "will not work."
        ) from e

    logger.info("GitHub App private key loaded from %s", source)
    return pem


class GitHubClient:
    def __init__(self, repo_name: str | None = None):
        """A GitHub client scoped to ``repo_name`` when reviewing one repository.

        Under App auth the token has to come from *the installation that owns the
        repo*. A GitHub App is installed once per account, so the installation that
        can see ``alice/api`` is a different one from the installation that can see
        ``bob/api`` — a single GITHUB_APP_INSTALLATION_ID only ever works for the one
        account it was issued for, and every other account's pull requests fail with
        a 404 that reads like the repo does not exist. Passing the repo lets the
        installation be looked up from the App itself.
        """
        load_dotenv()

        self._repo_name = repo_name

        if os.getenv("GITHUB_APP_ID"):
            self._auth_as_github_app()
        else:
            self._auth_as_pat()

    def _auth_as_pat(self):
        self.token = os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment")

        self.client = Github(self.token)

    @classmethod
    def app_slug(cls) -> str | None:
        """This App's slug, for building its install URL. None if it cannot be read."""
        load_dotenv()

        app_id = os.getenv("GITHUB_APP_ID")
        if not app_id:
            return None

        try:
            response = requests.get(
                "https://api.github.com/app",
                headers={
                    "Authorization": f"Bearer {cls._app_jwt(app_id, cls._load_private_key())}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=10,
            )
        except (requests.RequestException, ValueError):
            logger.warning("Could not read the App's slug", exc_info=True)
            return None

        if response.status_code != 200:
            logger.warning("Could not read the App's slug: %s", response.text)
            return None

        return response.json().get("slug")

    @classmethod
    def is_app_installed_on(cls, repo_name: str) -> bool | None:
        """Whether this App is installed on ``repo_name``.

        None means the question could not be answered — no App configured, or GitHub
        could not be reached. Callers must treat that as "don't know", never as "not
        installed", so a transient failure cannot tell a user their working repo is
        broken.
        """
        load_dotenv()

        app_id = os.getenv("GITHUB_APP_ID")
        if not app_id:
            return None

        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo_name}/installation",
                headers={
                    "Authorization": f"Bearer {cls._app_jwt(app_id, cls._load_private_key())}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=10,
            )
        except (requests.RequestException, ValueError):
            logger.warning("Could not check the App installation for %s", repo_name, exc_info=True)
            return None

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False

        logger.warning(
            "Unexpected reply checking the App installation for %s: %s",
            repo_name,
            response.status_code,
        )
        return None

    @classmethod
    def verify_app_credentials(cls) -> None:
        """Prove the App's id and private key are usable. Raises if they are not.

        There is no installation token to fetch here: installations are resolved per
        repo at review time. This is the most that can be checked without a repo, and
        it is what a boot-time check needs — a key that cannot sign is the failure
        that silently stops every review.
        """
        load_dotenv()

        app_id = os.getenv("GITHUB_APP_ID")
        if not app_id:
            raise ValueError("GITHUB_APP_ID not found in environment")

        cls._app_jwt(app_id, cls._load_private_key())

    @staticmethod
    def _load_private_key() -> str:
        """The GitHub App private key, from whichever source is available.

        Three sources, in order: a .pem on disk, the key itself, or the key base64
        encoded. All three are tried rather than the first that is *configured*,
        because `*.pem` is both git- and docker-ignored — the key file does not exist
        in a deployed image. A GITHUB_APP_PRIVATE_KEY_PATH left over from a local
        checkout must therefore fall through to the environment instead of failing
        the whole process with a FileNotFoundError.

        Whatever comes back is canonicalised and then verified to actually parse as a
        private key, so a mangled value fails here — naming the variable it came from
        — rather than a hundred lines later inside PyJWT as "could not parse the
        provided public key".
        """
        key_path_str = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        if key_path_str:
            key_path = Path(key_path_str)
            if not key_path.is_absolute():
                key_path = PROJECT_ROOT / key_path
            try:
                with open(key_path, "r") as f:
                    return _validated_pem(f.read(), f"GITHUB_APP_PRIVATE_KEY_PATH ({key_path})")
            except OSError:
                logger.warning(
                    "GITHUB_APP_PRIVATE_KEY_PATH points at %s, which cannot be read; "
                    "falling back to the key in the environment",
                    key_path,
                )

        for variable in ("GITHUB_APP_PRIVATE_KEY_B64", "GITHUB_APP_PRIVATE_KEY"):
            value = os.getenv(variable)
            if value:
                return _validated_pem(value, variable)

        raise ValueError(
            "Neither GITHUB_APP_PRIVATE_KEY_PATH (readable), GITHUB_APP_PRIVATE_KEY nor "
            "GITHUB_APP_PRIVATE_KEY_B64 yielded a private key. In a container the key "
            "file is not present, so set GITHUB_APP_PRIVATE_KEY_B64."
        )

    @staticmethod
    def _app_jwt(app_id: str, private_key: str) -> str:
        payload = {
            "iat": int(time.time()) - 60,         # issued at (60 seconds ago to allow clock drift)
            "exp": int(time.time()) + (10 * 60),  # expires in 10 minutes (GitHub's max)
            "iss": app_id,                        # issuer = your App ID
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    def get_authenticated_login(self) -> str | None:
        """The login that authors this client's comments, or None if unknowable.

        Needed to recognise PRLens's own comments on a PR — the only safe basis for
        deleting them on a re-review. An installation posts as the App's bot user
        ("<app-slug>[bot]"), which is not derivable from the installation token, so
        the App itself has to be asked. Cached: it cannot change for a process.

        None means "could not tell", and every caller must then leave comments
        alone rather than guess, because the cost of guessing wrong is deleting
        somebody else's comment.
        """
        if hasattr(self, "_authenticated_login"):
            return self._authenticated_login

        self._authenticated_login = None
        try:
            if getattr(self, "_app_id", None):
                response = requests.get(
                    "https://api.github.com/app",
                    headers={
                        "Authorization": f"Bearer {self._app_jwt(self._app_id, self._private_key)}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    slug = response.json().get("slug")
                    if slug:
                        self._authenticated_login = f"{slug}[bot]"
                else:
                    logger.warning("Could not read the App's identity: %s", response.text)
            else:
                self._authenticated_login = self.client.get_user().login
        except (requests.RequestException, GithubException, ValueError, KeyError):
            logger.warning("Could not determine the authenticated GitHub identity", exc_info=True)

        return self._authenticated_login

    def _installation_id_for_repo(self, app_id: str, private_key: str, repo_name: str) -> str:
        """The id of the installation of this App on ``repo_name``.

        Raises when the App is not installed there: that is the one failure a repo
        owner can actually fix, so it must not be papered over by falling back to
        some other account's installation — whose token cannot read the repo either,
        but fails much later and much less legibly.
        """
        response = requests.get(
            f"https://api.github.com/repos/{repo_name}/installation",
            headers={
                "Authorization": f"Bearer {self._app_jwt(app_id, private_key)}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )

        if response.status_code == 404:
            raise ValueError(
                f"The PRLens GitHub App is not installed on '{repo_name}'. Enabling the "
                "repo in the dashboard only records it in PRLens; the App still has to "
                "be installed on the account that owns the repo, and granted access to "
                "it, before GitHub will send pull request events."
            )
        if response.status_code != 200:
            raise ValueError(
                f"Could not find the App installation for '{repo_name}': "
                f"{response.status_code} {response.text}"
            )

        return str(response.json()["id"])

    def _auth_as_github_app(self):
        private_key = getattr(self, '_private_key', None)
        app_id = getattr(self, '_app_id', None)
        installation_id = getattr(self, '_installation_id', None)
        repo_name = getattr(self, '_repo_name', None)

        if not private_key:
            private_key = self._load_private_key()

        if not app_id:
            app_id = os.getenv("GITHUB_APP_ID")
            if not app_id:
                raise ValueError("GITHUB_APP_ID not found in environment")

        if not installation_id:
            if repo_name:
                # Ask the App which installation owns this repo. GITHUB_APP_INSTALLATION_ID
                # is not consulted: it is a single account's installation, and honouring it
                # here is what stopped repos on every *other* account from being reviewed.
                installation_id = self._installation_id_for_repo(app_id, private_key, repo_name)
            else:
                installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
                if not installation_id:
                    raise ValueError("GITHUB_APP_INSTALLATION_ID not found in environment")

        jwt_token = self._app_jwt(app_id, private_key)

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


