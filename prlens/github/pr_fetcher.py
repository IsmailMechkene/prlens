from prlens.github.client import GitHubClient
from prlens.models.pr import PR, FileChange, FileChangeStatus, PRStatus


class PRFetcher:
    def __init__(self, client: GitHubClient):
        self.client = client

    def fetch(self, repo_name: str, pr_number: int) -> PR:
        repo = self.client.get_repo(repo_name)
        pull_request = repo.get_pull(pr_number)

        return PR(
            title=pull_request.title,
            author=pull_request.user.login,
            body=pull_request.body,
            number=pull_request.number,
            repo=repo_name,
            status=PRStatus(pull_request.state),
            source_branch=pull_request.head.ref,
            target_branch=pull_request.base.ref,
            labels=[label.name for label in pull_request.labels],
            reviewers=[user.login for user in pull_request.get_review_requests()[0]],
            files=[
                FileChange(
                    filename=file.filename,
                    status=FileChangeStatus(file.status),
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=file.patch
                )
                for file in pull_request.get_files()
            ]
        )




