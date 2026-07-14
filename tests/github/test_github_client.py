import base64
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from github import GithubException

from prlens.github.client import GitHubClient

# A real key: the client now verifies that what it loaded actually parses as a
# private key, so a placeholder string is (correctly) rejected. Generated once for
# the module — it never leaves the test process.
TEST_PEM = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,  # PKCS#1, as GitHub issues it
    serialization.NoEncryption(),
).decode()


def _env(mapping):
    """Build an os.getenv stub backed by ``mapping`` (missing keys -> default)."""
    def getenv(key, default=None):
        return mapping.get(key, default)
    return getenv


def _post_response(token="inst-token", status=201, message="boom"):
    resp = MagicMock(name="Response")
    resp.status_code = status
    resp.json.return_value = {"token": token} if status == 201 else {"message": message}
    return resp


# Minimal environment that routes GitHubClient into GitHub App auth.
APP_ENV = {
    "GITHUB_APP_ID": "123",
    "GITHUB_APP_PRIVATE_KEY": TEST_PEM,
    "GITHUB_APP_INSTALLATION_ID": "456",
}


def _pat_env(key, default=None):
    """os.getenv stub that enables PAT auth only.

    Returns the token for GITHUB_TOKEN and the default (None) for everything
    else — crucially GITHUB_APP_ID, so the client does not take the GitHub
    App auth branch.
    """
    return "ghp_token" if key == "GITHUB_TOKEN" else default


def test_init_raises_without_token():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", return_value=None):
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            GitHubClient()


def test_init_creates_client_with_token():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_pat_env), \
         patch("prlens.github.client.Github") as mock_github:
        client = GitHubClient()

        assert client.token == "ghp_token"
        mock_github.assert_called_once_with("ghp_token")
        assert client.client == mock_github.return_value


def test_get_repo_returns_repository():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_pat_env), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

        repo = MagicMock(name="Repository")
        client.client.get_repo.return_value = repo

        result = client.get_repo("owner/repo")

        client.client.get_repo.assert_called_once_with("owner/repo")
        assert result == repo


def test_get_repo_raises_on_github_exception():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_pat_env), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

        client.client.get_repo.side_effect = GithubException(
            404, {"message": "Not Found"}, {}
        )

        with pytest.raises(ValueError, match="Could not access repository"):
            client.get_repo("owner/missing")


# ---------------------------------------------------------------------------
# GitHub App authentication
# ---------------------------------------------------------------------------

def test_init_authenticates_as_github_app():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt") as mock_jwt, \
         patch("prlens.github.client.requests.post", return_value=_post_response("inst-token")) as mock_post, \
         patch("prlens.github.client.Github") as mock_github:
        client = GitHubClient()

    # JWT signed with the App's private key using RS256, issued by the App ID.
    payload, key = mock_jwt.call_args.args
    assert key == TEST_PEM
    assert payload["iss"] == "123"
    assert mock_jwt.call_args.kwargs["algorithm"] == "RS256"

    # Installation token exchanged for the correct installation.
    assert "/app/installations/456/access_tokens" in mock_post.call_args.args[0]
    mock_github.assert_called_once_with("inst-token")

    # Credentials cached for later refreshes.
    assert client._app_id == "123"
    assert client._private_key == TEST_PEM
    assert client._installation_id == "456"
    assert client._token_expiry > int(time.time())


def _get_response(payload=None, status=200):
    resp = MagicMock(name="Response")
    resp.status_code = status
    resp.json.return_value = payload if payload is not None else {}
    resp.text = "not found" if status == 404 else "ok"
    return resp


def test_repo_scoped_client_resolves_the_installation_that_owns_the_repo():
    # The regression this guards: GITHUB_APP_INSTALLATION_ID is one account's
    # installation. Honouring it for a repo on a *different* account produced a token
    # that cannot see the repo, and the pull request was never reviewed.
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.get", return_value=_get_response({"id": 999})) as mock_get, \
         patch("prlens.github.client.requests.post", return_value=_post_response()) as mock_post, \
         patch("prlens.github.client.Github"):
        client = GitHubClient("other-account/test")

    assert "/repos/other-account/test/installation" in mock_get.call_args.args[0]
    # 999 (the repo's own installation), not 456 (the environment's).
    assert "/app/installations/999/access_tokens" in mock_post.call_args.args[0]
    assert client._installation_id == "999"


def test_repo_scoped_client_raises_when_the_app_is_not_installed():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.get", return_value=_get_response(status=404)), \
         patch("prlens.github.client.Github"):
        with pytest.raises(ValueError, match="not installed on 'other-account/test'"):
            GitHubClient("other-account/test")


def test_unscoped_client_still_uses_the_environment_installation():
    # GitHub Actions mode passes the installation id explicitly and has no App-wide
    # JWT lookup to make; that path must keep working.
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.get") as mock_get, \
         patch("prlens.github.client.requests.post", return_value=_post_response()) as mock_post, \
         patch("prlens.github.client.Github"):
        GitHubClient()

    mock_get.assert_not_called()
    assert "/app/installations/456/access_tokens" in mock_post.call_args.args[0]


@pytest.mark.parametrize("status, expected", [(200, True), (404, False), (500, None)])
def test_is_app_installed_on(status, expected):
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.get", return_value=_get_response({"id": 1}, status)):
        assert GitHubClient.is_app_installed_on("acme/api") is expected


def test_is_app_installed_on_is_unknown_when_github_is_unreachable():
    # Must be None, never False: a transient failure telling a user their App is not
    # installed would send them off to reinstall a working App.
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.get", side_effect=requests.RequestException("down")):
        assert GitHubClient.is_app_installed_on("acme/api") is None


def test_app_auth_reads_private_key_from_path():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_PRIVATE_KEY_PATH": "app-key.pem",
        "GITHUB_APP_INSTALLATION_ID": "456",
    }
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("builtins.open", mock_open(read_data=TEST_PEM)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt") as mock_jwt, \
         patch("prlens.github.client.requests.post", return_value=_post_response()), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

    assert client._private_key == TEST_PEM
    assert mock_jwt.call_args.args[1] == TEST_PEM


def test_app_auth_raises_when_no_private_key():
    env = {"GITHUB_APP_ID": "123", "GITHUB_APP_INSTALLATION_ID": "456"}
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("prlens.github.client.Github"):
        with pytest.raises(ValueError, match="Neither GITHUB_APP_PRIVATE_KEY_PATH"):
            GitHubClient()


def test_app_auth_raises_when_no_installation_id():
    env = {"GITHUB_APP_ID": "123", "GITHUB_APP_PRIVATE_KEY": TEST_PEM}
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("prlens.github.client.Github"):
        with pytest.raises(ValueError, match="GITHUB_APP_INSTALLATION_ID"):
            GitHubClient()


def test_auth_as_github_app_raises_when_no_app_id():
    # Exercise the defensive app_id guard directly (unreachable via __init__,
    # which only calls this branch when GITHUB_APP_ID is already set).
    client = object.__new__(GitHubClient)
    env = {"GITHUB_APP_PRIVATE_KEY": TEST_PEM}
    with patch("prlens.github.client.os.getenv", side_effect=_env(env)):
        with pytest.raises(ValueError, match="GITHUB_APP_ID not found"):
            client._auth_as_github_app()


def test_app_auth_raises_on_non_201_response():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.post", return_value=_post_response(status=500)), \
         patch("prlens.github.client.Github"):
        with pytest.raises(ValueError, match="Failed to get installation token"):
            GitHubClient()


def test_refresh_reauthenticates_with_stored_credentials():
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(APP_ENV)), \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt"), \
         patch("prlens.github.client.requests.post", return_value=_post_response("token-1")), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

    # Force the token to look (nearly) expired so a refresh is triggered.
    client._token_expiry = int(time.time()) - 1

    with patch("prlens.github.client.os.getenv") as mock_getenv, \
         patch("prlens.github.client.jwt.encode", return_value="signed.jwt2"), \
         patch("prlens.github.client.requests.post", return_value=_post_response("token-2")) as mock_post, \
         patch("prlens.github.client.Github") as mock_github:
        client._refresh_token_if_needed()

    # Stored credentials are reused — no environment lookups on refresh.
    mock_getenv.assert_not_called()
    mock_post.assert_called_once()
    mock_github.assert_called_once_with("token-2")


def test_refresh_noop_when_token_is_fresh():
    client = object.__new__(GitHubClient)
    client._token_expiry = int(time.time()) + 3600
    client._auth_as_github_app = MagicMock()

    client._refresh_token_if_needed()

    client._auth_as_github_app.assert_not_called()


# ---------------------------------------------------------------------------
# Private key loading: a PEM rarely survives a hosting dashboard intact
# ---------------------------------------------------------------------------

MANGLED_KEYS = {
    "escaped newlines": TEST_PEM.replace("\n", "\n"),
    "collapsed onto one line": TEST_PEM.replace("\n", " "),
    "wrapped in quotes": f'"{TEST_PEM}"',
    "crlf line endings": TEST_PEM.replace("\n", "\r\n"),
}


@pytest.mark.parametrize("mangled", MANGLED_KEYS.values(), ids=list(MANGLED_KEYS))
def test_app_auth_repairs_a_mangled_pem(mangled):
    """The key still signs even when the environment mangled its newlines.

    This is the failure that stopped every review in production: PyJWT rejected the
    value with "Could not parse the provided public key".
    """
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_INSTALLATION_ID": "456",
        "GITHUB_APP_PRIVATE_KEY": mangled,
    }
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("prlens.github.client.requests.post", return_value=_post_response()), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

    assert client._private_key == TEST_PEM  # rebuilt into a canonical PEM


def test_app_auth_accepts_base64_encoded_key():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_INSTALLATION_ID": "456",
        "GITHUB_APP_PRIVATE_KEY_B64": base64.b64encode(TEST_PEM.encode()).decode(),
    }
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("prlens.github.client.requests.post", return_value=_post_response()), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

    assert client._private_key == TEST_PEM


def test_app_auth_falls_back_when_key_file_is_missing():
    """The .pem is not in the deployed image (*.pem is docker-ignored), so a stale
    GITHUB_APP_PRIVATE_KEY_PATH must not be fatal."""
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_INSTALLATION_ID": "456",
        "GITHUB_APP_PRIVATE_KEY_PATH": "not-in-the-image.pem",
        "GITHUB_APP_PRIVATE_KEY_B64": base64.b64encode(TEST_PEM.encode()).decode(),
    }
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("builtins.open", side_effect=FileNotFoundError), \
         patch("prlens.github.client.requests.post", return_value=_post_response()), \
         patch("prlens.github.client.Github"):
        client = GitHubClient()

    assert client._private_key == TEST_PEM


def test_app_auth_rejects_an_unusable_key_naming_its_variable():
    env = {
        "GITHUB_APP_ID": "123",
        "GITHUB_APP_INSTALLATION_ID": "456",
        "GITHUB_APP_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\nnope\n-----END RSA PRIVATE KEY-----",
    }
    with patch("prlens.github.client.load_dotenv"), \
         patch("prlens.github.client.os.getenv", side_effect=_env(env)), \
         patch("prlens.github.client.Github"):
        with pytest.raises(ValueError, match="GITHUB_APP_PRIVATE_KEY is not a usable private key"):
            GitHubClient()
