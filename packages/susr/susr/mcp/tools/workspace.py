"""susr.mcp.tools.workspace — Workspace lifecycle + KB MCP tools.

Per CLAUDE.md §8 decision 4 these replace the CLI subcommands we
deliberately did not ship (`susr init` / `susr doctor` / `susr kb-update`).

Tools (spec §6.3 + §6.4):
    create_client_workspace   — git init + DDL + frontmatter + shared/ snapshot
    health_check              — sqlite-vec / DDL / invariants / API key / embed
    update_shared_kb          — snapshot copy + diff + git commit in client repo
    promote_to_consultant_kb  — single-direction anonymize gate (KB信息流)

R1: signatures.  R2: implement.
"""

from __future__ import annotations

from typing import Literal, Optional


def create_client_workspace(
    name: str,
    legal_name: str,
    industry: str,
    standards: list[str],
    boundary: Literal["合併", "營運控制", "股權法"],
    reporting_period: str,
    embedding_policy: Literal["local", "cloud", "twostage"] = "twostage",
    pii_classification: Literal["high", "medium", "low"] = "medium",
) -> dict:
    """Create a new client workspace under SUSR_WORKSPACE_ROOT/<name>/.

    Scaffolds (spec §6.3):
        git init
        _client.md (with frontmatter from args)
        entities/{topics,stakeholders,governance,kpis,targets}/.gitkeep
        projects/, sourcedocs/
        .susr/db.sqlite   ← runs ddl/v001_init.sql
        shared/           ← snapshot copy from susr.shared_kb (NOT git submodule)

    Returns {workspace_path, initial_commit_hash, schema_version}.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.3")


def health_check(client_slug: Optional[str] = None) -> dict:
    """Verify the environment + (optionally) one client workspace.

    Checks (spec §6.3):
        1. sqlite-vec loads (and Python build supports enable_load_extension)
        2. shared_kb present and non-empty
        3. ANTHROPIC_API_KEY env present
        4. Default embedding provider importable + instantiates
        5. If client_slug given: schema_version, all invariants pass,
           shared/ snapshot vs package version diff

    Returns {ok, checks: [...], remediation: [...]}.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.3")


def update_shared_kb(client_slug: str, accept_changes: bool = False) -> dict:
    """Diff or apply a fresh shared_kb snapshot to a client repo.

    accept_changes=False → return the diff for consultant review.
    accept_changes=True  → write the snapshot + `git add` + commit in client repo.

    Consultants control upgrade cadence (e.g. environment ministry releases
    new emission factors mid-year and we DON'T want auto-retroactive change).
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.3")


def promote_to_consultant_kb(
    client_slug: str,
    client_page_slugs: list[str],
    anonymize_strategy: Literal["redact-pii", "generalize-numbers", "both"],
    target_kb_path: str,
    reviewer: str,
    confirm_token: str,
) -> dict:
    """Single-direction gate (CLAUDE.md §8 KB信息流): client → consultant-kb.

    Steps (spec §6.3):
        1. require confirm_token (consultant must dry_run first)
        2. anonymize selected pages per strategy
        3. write to consultant-kb repo path
        4. timeline_entries in client repo: action_type='comment',
           payload={promoted_to_kb, anonymize_strategy, reviewer}
        5. timeline_entries in consultant-kb:  action_type='ingest',
           payload={source_client, anonymize_strategy}

    Returns the audit log entry id + paths.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.3")
