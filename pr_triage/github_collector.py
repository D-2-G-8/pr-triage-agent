from pr_triage.models import PullRequest


def fetch_open_pull_requests(repo_full_name, client):
    """Return all open pull requests of a repository as PullRequest objects.

    The GitHub client is injected so the collector can be tested without
    hitting the network. PyGithub's PaginatedList is iterable and walks all
    pages transparently, so a plain loop covers repos with 200+ PRs.
    """
    repo = client.get_repo(repo_full_name)
    return [
        PullRequest(
            number=pr.number,
            title=pr.title,
            author=pr.user.login,
            state=pr.state,
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            html_url=pr.html_url,
            draft=pr.draft,
        )
        for pr in repo.get_pulls(state="open")
    ]
