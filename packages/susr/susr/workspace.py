"""susr.workspace — Per-client workspace lifecycle (shared logic).

Backs the `create_client_workspace` / `health_check` / `update_shared_kb`
MCP tools in susr.mcp.tools.workspace — keeping the actual filesystem +
git + DDL bootstrapping here lets tests reach the logic without the MCP
plumbing.

Workspace layout (spec §1.1):
    <root>/<name>/
        .git/
        .susr/db.sqlite
        _client.md
        entities/{topics,stakeholders,governance,kpis,targets}/.gitkeep
        projects/  sourcedocs/
        shared/        ← snapshot copy from susr.shared_kb.data
        .gitignore     ← excludes .susr/ (DB is derived)

R1: signatures only.  R2: implement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional


def create_client_workspace(
    root: Path,
    *,
    name: str,
    legal_name: str,
    industry: str,
    standards: list[str],
    boundary: Literal["合併", "營運控制", "股權法"],
    reporting_period: str,
    embedding_policy: Literal["local", "cloud", "twostage"] = "twostage",
    pii_classification: Literal["high", "medium", "low"] = "medium",
) -> dict:
    """Create a fresh client workspace + brain DB.

    Steps:
        1. mkdir <root>/<name>/ (fail if exists, non-empty)
        2. git init
        3. Scaffold entities/, projects/, sourcedocs/
        4. Write _client.md with the frontmatter from args
        5. BrainEngine.create_new(.susr/db.sqlite) — applies DDL v001
        6. snapshot_into(<name>, subdir='shared')
        7. .gitignore + initial commit
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §1.1 + §6.3")


def open_client_workspace(root: Path, name: str) -> dict:
    """Validate that <root>/<name>/ looks like a susr client workspace.

    Returns {path, schema_version, has_shared_snapshot, embedding_policy}.
    Raises FileNotFoundError if the brain DB is missing.
    """
    raise NotImplementedError("Step 1 R2")


def run_doctor(client_slug: Optional[str] = None) -> bool:
    """Print health-check results to stdout; return True iff all checks pass.

    Used by `susr-mcp doctor` (the only shell command in normal use) and by
    the `health_check` MCP tool.  See spec §9 for the expected output.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §9")
