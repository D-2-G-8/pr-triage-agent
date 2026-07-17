from pr_triage.models import ChangedFile, EnrichedPullRequest, LinkedIssue

_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      title
      body
      state
      isDraft
      author { login }
      labels(first: 100) { nodes { name } }
      commits(last: 1) {
        nodes { commit { statusCheckRollup { state } } }
      }
      closingIssuesReferences(first: 20) {
        nodes {
          number
          title
          state
          reactions(content: THUMBS_UP) { totalCount }
          comments { totalCount }
        }
      }
      files(first: 100) {
        nodes { path additions deletions }
        pageInfo { hasNextPage }
      }
    }
  }
}
"""


def _ci_status(pr):
    commits = pr["commits"]["nodes"]
    if not commits:
        return None
    rollup = commits[0]["commit"]["statusCheckRollup"]
    return rollup["state"] if rollup else None


def fetch_pr_enrichment(repo_full_name, number, execute):
    """Fetch structured GraphQL context for one PR (no diff text).

    ``execute`` is injected — it takes (query, variables) and returns the GraphQL
    ``data`` dict — so this mapping is testable without the network.
    """
    owner, name = repo_full_name.split("/", 1)
    data = execute(_QUERY, {"owner": owner, "name": name, "number": number})
    pr = data["repository"]["pullRequest"]

    author = pr["author"]["login"] if pr["author"] else None
    files = pr["files"]
    return EnrichedPullRequest(
        number=pr["number"],
        title=pr["title"],
        body=pr["body"],
        author=author,
        state=pr["state"],
        draft=pr["isDraft"],
        labels=[node["name"] for node in pr["labels"]["nodes"]],
        ci_status=_ci_status(pr),
        linked_issues=[
            LinkedIssue(
                number=node["number"],
                title=node["title"],
                state=node["state"],
                thumbs_up=node["reactions"]["totalCount"],
                comments_count=node["comments"]["totalCount"],
            )
            for node in pr["closingIssuesReferences"]["nodes"]
        ],
        changed_files=[
            ChangedFile(
                path=node["path"],
                additions=node["additions"],
                deletions=node["deletions"],
            )
            for node in files["nodes"]
        ],
        files_truncated=files["pageInfo"]["hasNextPage"],
    )
