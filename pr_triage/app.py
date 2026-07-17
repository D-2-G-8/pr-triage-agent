"""Top-level assembly: wire the tested units into a full backlog triage run.

This module is I/O glue over already-tested components (collector, enrichment,
diff, analysis, digest, runner). Validate it by running it, not by unit tests.
"""
import os

import anthropic
from dotenv import load_dotenv

from pr_triage.analysis import analyze_pr
from pr_triage.digest import build_digest, render_digest_markdown
from pr_triage.enrichment import fetch_pr_enrichment
from pr_triage.github_client import build_client
from pr_triage.github_graphql import GraphQLClient
from pr_triage.github_rest import RestClient
from pr_triage.github_collector import fetch_open_pull_requests
from pr_triage.pipeline import triage_pr
from pr_triage.repo_context import fetch_repo_context
from pr_triage.runner import run_backlog


def _build_get_text(repo):
    def get_text(path):
        try:
            return repo.get_contents(path).decoded_content.decode("utf-8", "ignore")
        except Exception:
            return None

    return get_text


def triage_repository(repo_full_name, limit=None, max_diff_chars=40000, max_attempts=3):
    """Run the full triage pipeline over a repo's open PRs.

    Returns (digest, markdown, run). ``limit`` caps how many PRs are processed
    (useful for smoke runs / cost control). Nothing is published anywhere — the
    returned digest is the artifact for manual review before any external action.
    """
    load_dotenv()
    token = os.environ["GITHUB_TOKEN"]

    gh = build_client()
    repo = gh.get_repo(repo_full_name)
    gql = GraphQLClient(token)
    rest = RestClient(token)
    claude = anthropic.Anthropic()

    repo_context = fetch_repo_context(_build_get_text(repo))
    prs = fetch_open_pull_requests(repo_full_name, gh)
    if limit is not None:
        prs = prs[:limit]

    def process(pr):
        return triage_pr(
            pr.number, pr.title,
            enrich=lambda n: fetch_pr_enrichment(repo_full_name, n, gql.execute),
            get_diff=lambda n: rest.fetch_pr_diff(repo_full_name, n),
            repo_context=repo_context,
            analyze=lambda e, d, ctx: analyze_pr(e, d, ctx, claude),
            max_diff_chars=max_diff_chars,
        )

    run = run_backlog(prs, process, max_attempts=max_attempts)
    digest = build_digest(run.results)
    markdown = render_digest_markdown(digest, repo_full_name)
    return digest, markdown, run


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m pr_triage.app <owner>/<repo> [limit]", file=sys.stderr)
        raise SystemExit(2)

    repo = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    digest, markdown, run = triage_repository(repo, limit=limit)
    print(markdown)
    if run.failures:
        print(f"\n{len(run.failures)} PR(s) failed:", file=sys.stderr)
        for f in run.failures:
            print(f"  #{getattr(f.item, 'number', f.item)}: {f.error}", file=sys.stderr)
