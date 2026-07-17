# PR Triage Agent

An LLM agent that triages the open-PR backlog of **any public GitHub repository** and
produces a digest of *what is actually ready for human review* — instead of a raw
list of hundreds of pull requests. Point it at any `owner/repo`.

## Why

Popular open-source repos accumulate PRs faster than maintainers can review them. A
repo's own CI already answers *"does this PR pass the technical bar"* (lint, tests,
automated review). What's missing is the layer that answers *"which of these is worth
a human's attention today"* — separating PRs with a real, current problem from
duplicates, stale requests, and low-value changes, with reasoning grounded in **that
repo's own** DoD/AC (`CONTRIBUTING.md`, PR template, CI status) rather than invented
criteria. Because the grounding comes from each repository's own files, the tool
adapts to whatever repo you run it against.

The first proving ground is
[`anthropics/claude-cookbooks`](https://github.com/anthropics/claude-cookbooks)
(213 open PRs), but nothing in the code is specific to it.

## How it works

For each open PR the agent runs a **cost-tiered** pipeline — cheap checks first, the
expensive model only where it earns its keep:

1. **List** open PRs via the GitHub REST API (PyGithub, auto-paginated).
2. **Enrich** each PR in one GitHub **GraphQL** query (metadata only, no diff):
   labels, CI check rollup, linked issues (`closingIssuesReferences`) with their
   👍/comment engagement, the changed-file list, and whether the author is a bot.
3. **Tier 0 — bot filter (free, no LLM):** PRs from automation accounts
   (dependabot, renovate, `[bot]` suffix, GitHub's bot flag) get a canned `low_value`
   verdict without any model call.
4. **Tier 1 — cheap screen (`claude-haiku-4-5`, metadata only, no diff):** a fast
   model decides whether each PR is worth a full review. The obviously low-value /
   stale / duplicate are skipped here for a fraction of a cent.
5. **Tier 2 — deep analysis (`claude-opus-4-8`) — survivors only:** fetch the diff
   via REST and **cap** it (large notebook diffs truncated with an explicit marker),
   then analyze against the repo's own `CONTRIBUTING.md` + PR template, returning five
   fields: `summary`, `problem_statement`, `dod_ac_status`, `reality_assessment`,
   `recommended_category` (`ready_for_review` / `likely_duplicate` / `stale` /
   `low_value`).
6. **Aggregate** into a digest — `ready_for_review` first, capped to a top-N, with a
   category breakdown — rendered as Markdown.

Because the diff (which dominates token cost) and the expensive model are reached only
in Tier 2, cost grows **sublinearly** when a backlog fills with bot/low-value PRs — a
flood of automated PRs is filtered for near-zero cost instead of paying full price per PR.

The run is resilient: transient errors (e.g. rate limits) are retried with backoff,
and a single failing PR is recorded rather than aborting the whole pass. **Nothing is
published anywhere** — the digest is the artifact for manual review.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then either **activate the venv** (so a plain `python` resolves to it)…

```bash
source .venv/bin/activate       # deactivate with: deactivate
```

…or just call the venv's interpreter directly as `.venv/bin/python` (used in the
examples below). Running with the system `python3` will fail with
`ModuleNotFoundError: No module named 'github'` because the dependencies live in the
venv, not the system Python.

Create a `.env` file with two tokens:

```
GITHUB_TOKEN=ghp_your_read_only_token
ANTHROPIC_API_KEY=sk-ant-your_key
```

- `GITHUB_TOKEN` — read-only GitHub personal access token (public data only).
- `ANTHROPIC_API_KEY` — needed only for the Claude analysis step; listing/enriching
  PRs works without it.

## Running

### CLI

```bash
.venv/bin/python -m pr_triage.app <owner>/<repo> [limit]
```

(or just `python -m pr_triage.app ...` if you activated the venv)

```bash
# smoke run on the first 3 open PRs of any repo (cheap — recommended first)
.venv/bin/python -m pr_triage.app owner/repo 3

# full backlog (all open PRs)
.venv/bin/python -m pr_triage.app owner/repo
```

Prints the Markdown digest to stdout (per-PR failures go to stderr). Redirect to save
it: `... owner/repo 3 > digest.md`.

> **Cost.** The tiered pipeline keeps the expensive model off most PRs: bots are free,
> the cheap screen is a fraction of a cent per PR, and only survivors pay for the deep
> `claude-opus-4-8` analysis. Deep analysis of a single PR runs ~$0.05–0.28 (diff-size
> dependent). A naive "Opus on every PR" pass over the 213-PR `anthropics/claude-cookbooks`
> backlog would be **≈ $16**; the tiering brings that down substantially and, crucially,
> keeps it from ballooning when the backlog fills with automated PRs. Start with a small
> `limit` to sanity-check output before running a whole backlog.

### Programmatic

```python
from pr_triage.app import triage_repository

digest, markdown, run = triage_repository("owner/repo", limit=3)

print(markdown)                       # the Markdown report
print(digest.counts)                  # {'ready_for_review': 3, 'likely_duplicate': 0, ...}
for assessed in digest.ready:         # top ready-for-review PRs
    print(assessed.number, assessed.assessment.recommended_category)
print("failures:", run.failures)      # PRs that failed after retries
```

You can also use the pieces directly — e.g. list PRs without any Claude calls:

```python
from dotenv import load_dotenv
from pr_triage.github_client import build_client
from pr_triage.github_collector import fetch_open_pull_requests

load_dotenv()
prs = fetch_open_pull_requests("owner/repo", build_client())
print(f"{len(prs)} open PRs")
```

## Project layout

```
pr_triage/
  models.py            # frozen dataclasses (PullRequest, EnrichedPullRequest,
                       #   LinkedIssue, ChangedFile, RepoContext, PRAssessment,
                       #   AssessedPR, Digest, TriageRun, ...)
  github_client.py     # build_client() -> authenticated PyGithub client
  github_collector.py  # fetch_open_pull_requests(repo, client)
  github_graphql.py    # GraphQLClient.execute(query, variables)
  github_rest.py       # RestClient.fetch_pr_diff(repo, number)  (raw unified diff)
  enrichment.py        # fetch_pr_enrichment(repo, number, execute) -> EnrichedPullRequest
  repo_context.py      # fetch_repo_context(get_text) -> RepoContext
  diff.py              # cap_diff(text, max_chars)
  prescreen.py         # Tier 0: is_bot_pr(...) + bot_assessment(...)  (free)
  screen.py            # Tier 1: screen_pr(...) cheap metadata-only screen (Haiku)
  analysis.py          # Tier 2: build_prompt(...) + analyze_pr(...) -> PRAssessment (Opus)
  digest.py            # build_digest(...) + render_digest_markdown(...)
  runner.py            # run_backlog(items, process, ...) with retries/backoff
  pipeline.py          # triage_pr_tiered(...) — cost-tiered per-PR composition
  app.py               # triage_repository(...) + CLI entry point
tests/                 # pytest suite (TDD)
```

Every unit takes its I/O collaborators (HTTP/GitHub/Claude clients) as injected
arguments, so the logic is unit-tested without network calls; `app.py` is the only
module that wires real clients together.

## Tests

Developed test-first (TDD). Pure logic and mappings are covered by fast, offline
unit tests (mocked clients — no network):

```bash
.venv/bin/python -m pytest
```

## Status

- **Phase 0 — recon:** ✅ done (API access, rate limits, measured token cost).
- **Phase 1 — v0 core (P0):** pipeline is feature-complete (list → enrich → diff →
  analyze → digest, with retry resilience). Remaining: a full backlog run and manual
  verification of the assessments. Repo-wide issue mining for stronger
  duplicate/reality detection is a follow-up.
- **Phase 2 — publish pilot** and **Phase 3 — outreach** are later.

## Conventions

- Everything inside this directory is written in **English** (code, comments, docs, commits).
- **Read-only** — the tool never writes to any analyzed repository (no comments, no
  labels). It uses only public data. Any external publication is a manual, deliberate step.
