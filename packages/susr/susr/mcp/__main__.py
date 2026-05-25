"""susr.mcp.__main__ — `susr-mcp` console script entry point.

Bound in pyproject.toml as:
    [project.scripts]
    susr-mcp = "susr.mcp.__main__:main"

Default command starts the FastMCP server over stdio (the form Claude
Desktop expects).  The `doctor` subcommand runs a health check.

This is the ONLY shell touchpoint for consultants after initial install
(CLAUDE.md §8 decision 4).  Everything else flows through MCP tools in
the chat client.

R1: stub.  R2: implement subcommand dispatch with typer.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Console-script entry. Dispatch to `serve` (default) or `doctor`.

    Argv parsing pattern (R2 will use typer):
        susr-mcp           → start stdio MCP server
        susr-mcp serve     → same as above (explicit)
        susr-mcp doctor    → run susr.workspace.run_doctor()
    """
    raise NotImplementedError(
        "Step 1 R2 — see docs/research/step1-spec.md §6.1 + susr.mcp.server"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main() or 0)
