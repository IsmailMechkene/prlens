from github import Github, Repository, GithubException
from dotenv import load_dotenv
import os

class GitHubClient:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment")

        self.client = Github(self.token)

    def get_repo(self, repo_name: str) -> Repository.Repository:
        try:
            repo = self.client.get_repo(repo_name)
        except GithubException as ge:
            raise ValueError(f"Could not access repository '{repo_name}': {ge}")
        return  repo


# TODO: Add GitHub App (JWT) support - US-1.1 CA-3 (Mazel bekri)