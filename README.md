# PR Triage Agent

An LLM agent that triages the open-PR backlog of a public GitHub repository and
produces a daily digest of *what is actually ready for human review* — instead of
a raw list of 200+ pull requests.

**v0 target repo:** [`anthropics/claude-cookbooks`](https://github.com/anthropics/claude-cookbooks)
(213 open PRs as of 2026-07-17).

## Why

Open repos of large AI companies accumulate PRs faster than maintainers can review
them. The repo's own CI already answers *"does this PR pass the technical bar"*
(lint, notebook validation, automated review). What's missing is the layer that
answers *"which of these is worth a human's attention today"* — separating PRs with
a real, current problem from duplicates, stale requests, and low-value changes, with
reasoning grounded in the repo's own DoD/AC (`CONTRIBUTING.md`, PR template, CI
status) rather than invented criteria.

## Status

Phase 0 (technical recon) — in progress. Implemented so far:

- **Data collector (P0):** fetch all open PRs of a repository via the GitHub API.

Recon so far confirms GitHub API access and rate-limit headroom for a full backlog
pass, and estimates the cost of analyzing all 213 open PRs at **≈ $13 on Opus 4.8**
(≈ $8 on Sonnet 5) — cheap enough to run whole.

## Project layout

```
pr_triage/
  models.py            # PullRequest dataclass (frozen, GitHub-agnostic)
  github_collector.py  # fetch_open_pull_requests(repo, client) -> list[PullRequest]
  github_client.py     # build_client() -> authenticated PyGithub client
tests/                 # pytest suite (TDD)
```

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create a `.env` file with a read-only GitHub personal access token:

```
GITHUB_TOKEN=ghp_your_token_here
```

## Usage

```python
from dotenv import load_dotenv

from pr_triage.github_client import build_client
from pr_triage.github_collector import fetch_open_pull_requests

load_dotenv()
client = build_client()  # reads GITHUB_TOKEN from the environment
prs = fetch_open_pull_requests("anthropics/claude-cookbooks", client)

print(f"{len(prs)} open PRs")
for pr in prs[:5]:
    print(f"#{pr.number} @{pr.author} — {pr.title}")
```

Each result is an immutable `PullRequest` with `number`, `title`, `author`, `state`,
`created_at`, `updated_at`, `html_url`, and `draft`.

## Tests

Developed test-first (TDD). The collector is unit-tested against an injected,
mocked GitHub client — no network calls.

```bash
.venv/bin/python -m pytest
```

## Roadmap

- **Phase 0** — recon: API access, rate limits, 10-PR sample, token-cost estimate. *(in progress)*
- **Phase 1 — v0 core (P0):** per-PR enrichment (diff/files, CI status, linked issue,
  labels), CONTRIBUTING/PR-template context, issues with reactions/comments, the
  Claude analysis call (5 structured fields per PR), and the digest.
- **Phase 2 — publish pilot:** findings on 5–10 PRs, gauge reception.
- **Phase 3 — outreach.**

**Near-term next step:** introduce GraphQL for per-PR enrichment (diff, CI checks,
linked issues, reactions in one query) to cut round-trips and rate-limit pressure at
200+ PRs — the open-PR *list* stays on REST (PyGithub) as it is now.

## Conventions

- Everything inside this directory is written in **English** (code, comments, docs, commits).
- No write actions against `anthropics/claude-cookbooks` — read-only public data only.
  Any external publication is a manual, deliberate step.
