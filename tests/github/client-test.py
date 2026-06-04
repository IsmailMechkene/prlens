from prlens.github.client import GitHubClient

client = GitHubClient()
repo = client.get_repo("IsmailMechkene/ai-pr-reviewer-test")
print(repo.name)
print(repo.owner.login)
