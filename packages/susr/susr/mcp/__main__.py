"""susr.mcp.__main__ — `susr-mcp` console script entry point.

Bound in pyproject.toml as:
    [project.scripts]
    susr-mcp = "susr.mcp.__main__:main"

Default command starts the FastMCP server over stdio (the form Claude
Desktop expects).  The `doctor` subcommand runs a health check.

This is the ONLY shell touchpoint for consultants after initial install
(CLAUDE.md §8 decision 4).  Everything else flows through MCP tools in
the chat client.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Console-script entry. Dispatch to `serve` (default) or `doctor`.

    Argv pattern:
        susr-mcp           → start stdio MCP server (default)
        susr-mcp serve     → same as above (explicit)
        susr-mcp doctor    → run susr.workspace.run_doctor()
    """
    argv = sys.argv[1:]
    command = argv[0] if argv else "serve"

    if command in ("serve", ""):
        # Lazy import — `mcp` SDK is the heaviest dep, keep import-time light.
        from .server import serve

        serve(transport="stdio")
        return 0

    if command == "doctor":
        from susr.workspace import run_doctor

        ok = run_doctor()
        return 0 if ok else 1

    sys.stderr.write(
        f"susr-mcp: unknown command {command!r}\n"
        f"usage: susr-mcp [serve|doctor]\n"
    )
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main() or 0)
