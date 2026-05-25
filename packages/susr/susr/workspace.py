"""susr.workspace — Per-client workspace lifecycle (shared logic).

Backs the create_client_workspace / health_check / update_shared_kb MCP
tools.  Layout (spec §1.1):

    <root>/<name>/
        .git/
        .susr/db.sqlite
        _client.md
        entities/{topics,stakeholders,governance,kpis,targets}/.gitkeep
        projects/  sourcedocs/
        shared/       ← snapshot copy of susr.shared_kb.data
        .gitignore    ← excludes .susr/ (DB is derived)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

from susr.shared_kb.snapshot import diff_against, snapshot_into


def workspace_root() -> Path:
    """$SUSR_WORKSPACE_ROOT or fallback ~/susr-clients/."""
    env = os.environ.get("SUSR_WORKSPACE_ROOT")
    return Path(env).expanduser() if env else Path.home() / "susr-clients"


def find_client_workspace(name: str, root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else workspace_root()
    path = base / name
    if not (path / "_client.md").exists():
        raise FileNotFoundError(f"no susr client workspace at {path}")
    return path


def get_client_db_path(name: str, root: Optional[Path] = None) -> Path:
    return find_client_workspace(name, root=root) / ".susr" / "db.sqlite"


def _yaml_dump(payload: dict) -> str:
    import yaml  # type: ignore

    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def _client_md_body(name: str, legal_name: str, industry: str) -> str:
    return (
        f"# {legal_name}\n\n- Slug: `{name}`\n- Industry: {industry}\n\n"
        "## Profile\n\n_<edit here — add board / reporting boundary / contacts>_\n\n"
        "---\n\n## Timeline\n\n"
        "<!-- timeline_entries 由 susr 自動追加；不要手改 -->\n"
    )


def _git(args: list[str], cwd: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), check=False,
            capture_output=True, text=True, encoding="utf-8",
        )
    except FileNotFoundError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _git_init_and_commit(path: Path, message: str) -> Optional[str]:
    """Best-effort init + first commit; tolerates missing git."""
    if _git(["init", "-q"], path) is None:
        return None
    if _git(["config", "user.email", "susr@local"], path) is None:
        return None
    _git(["config", "user.name", "susr"], path)
    _git(["add", "."], path)
    _git(["commit", "-q", "-m", message], path)
    return _git(["rev-parse", "HEAD"], path)


GITIGNORE_TEMPLATE = "# susr per-client repo\n.susr/\n.DS_Store\n__pycache__/\n*.pyc\n"


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

    Returns workspace_path / initial_commit_hash / schema_version /
    shared_snapshot_files / shared_version.
    """
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    path = base / name
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"workspace path {path} already exists and is non-empty")
    path.mkdir(parents=True, exist_ok=True)

    for sub in (
        "entities/topics", "entities/stakeholders", "entities/governance",
        "entities/kpis", "entities/targets", "projects", "sourcedocs", ".susr",
    ):
        (path / sub).mkdir(parents=True, exist_ok=True)
        if sub.startswith("entities/"):
            (path / sub / ".gitkeep").write_text("", encoding="utf-8")

    fm = {
        "slug": name, "legal_name": legal_name, "industry_gri_sector": industry,
        "boundary": boundary, "reporting_period": reporting_period,
        "applicable_standards": list(standards),
        "embedding_policy": embedding_policy, "pii_classification": pii_classification,
    }
    (path / "_client.md").write_text(
        "---\n" + _yaml_dump(fm) + "---\n\n" + _client_md_body(name, legal_name, industry),
        encoding="utf-8",
    )
    (path / ".gitignore").write_text(GITIGNORE_TEMPLATE, encoding="utf-8")

    snap = snapshot_into(path, subdir="shared", overwrite=False)

    schema_version: Optional[int] = None
    try:
        from susr.brain.engine import BrainEngine

        engine = BrainEngine.create_new(str(path / ".susr" / "db.sqlite"))
        try:
            row = engine.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            schema_version = int(row[0]) if row and row[0] is not None else None
        except Exception:  # pragma: no cover
            pass
        finally:
            try:
                engine.close()
            except Exception:  # pragma: no cover
                pass
    except NotImplementedError:
        # BrainEngine still a stub from a sibling agent — don't block.
        pass

    commit = _git_init_and_commit(path, f"chore(susr): initialise client workspace {name}")
    return {
        "workspace_path": str(path), "initial_commit_hash": commit,
        "schema_version": schema_version,
        "shared_snapshot_files": snap.get("files_copied"),
        "shared_version": snap.get("source_version"),
        "embedding_policy": embedding_policy,
    }


def open_client_workspace(root: Path, name: str) -> dict:
    path = Path(root) / name
    if not (path / "_client.md").exists():
        raise FileNotFoundError(f"no _client.md under {path}")
    db_path = path / ".susr" / "db.sqlite"
    if not db_path.exists():
        raise FileNotFoundError(f"no brain DB at {db_path}")
    schema_version: Optional[int] = None
    try:
        from susr.brain.engine import BrainEngine

        engine = BrainEngine.open(str(db_path))
        try:
            row = engine.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            schema_version = int(row[0]) if row and row[0] is not None else None
        finally:
            engine.close()
    except (NotImplementedError, Exception):
        pass
    return {
        "path": str(path), "schema_version": schema_version,
        "has_shared_snapshot": (path / "shared").exists(),
        "embedding_policy": os.environ.get("SUSR_EMBEDDING_PROVIDER"),
    }


def _check_sqlite_vec() -> tuple[bool, str]:
    import sqlite3

    if not hasattr(sqlite3.Connection, "enable_load_extension"):
        return False, (
            "this Python build lacks enable_load_extension "
            "(macOS system Python — use Homebrew or python.org)"
        )
    try:
        import sqlite_vec  # type: ignore  # noqa: F401
    except ImportError as e:
        return False, f"sqlite-vec not installed: {e}"
    return True, "sqlite-vec available"


def _check_shared_kb() -> tuple[bool, str]:
    from susr.shared_kb import SHARED_KB_DATA_DIR

    if not SHARED_KB_DATA_DIR.exists():
        return False, f"shared_kb data dir absent: {SHARED_KB_DATA_DIR}"
    n = sum(1 for p in SHARED_KB_DATA_DIR.rglob("*") if p.is_file())
    return True, f"shared_kb present ({n} files)"


def _check_anthropic_key() -> tuple[bool, str]:
    return (
        (True, "ANTHROPIC_API_KEY set")
        if os.environ.get("ANTHROPIC_API_KEY")
        else (False, "ANTHROPIC_API_KEY not set")
    )


def health_checks(client_slug: Optional[str] = None) -> dict:
    """Run env + optional client checks (spec §6.3)."""
    checks: list[dict] = []
    remediation: list[str] = []
    for label, fn in (
        ("python", lambda: (True, sys.version.split()[0])),
        ("sqlite-vec", _check_sqlite_vec),
        ("shared_kb", _check_shared_kb),
        ("ANTHROPIC_API_KEY", _check_anthropic_key),
        ("embedding_provider", lambda: (True, os.environ.get("SUSR_EMBEDDING_PROVIDER", "bge:bge-m3"))),
    ):
        try:
            ok, msg = fn()
        except Exception as e:  # pragma: no cover
            ok, msg = False, f"check raised: {e}"
        checks.append({"name": label, "ok": ok, "detail": msg})
        if not ok and label == "ANTHROPIC_API_KEY":
            remediation.append("export ANTHROPIC_API_KEY=sk-ant-...")
        if not ok and label == "sqlite-vec":
            remediation.append("pip install sqlite-vec ; use Homebrew / python.org Python on macOS")

    if client_slug:
        try:
            path = find_client_workspace(client_slug)
            checks.append({"ok": True, "name": "client", "detail": f"workspace at {path}"})
        except FileNotFoundError as e:
            checks.append({"ok": False, "name": "client", "detail": str(e)})

    root = workspace_root()
    known = (
        [p.name for p in sorted(root.iterdir()) if (p / "_client.md").exists()]
        if root.exists()
        else []
    )
    return {
        "ok": all(c["ok"] for c in checks),
        "checks": checks, "remediation": remediation,
        "known_workspaces": known, "workspace_root": str(root),
    }


def run_doctor(client_slug: Optional[str] = None) -> bool:
    """Print health-check results to stdout; True iff all pass."""
    result = health_checks(client_slug)
    for c in result["checks"]:
        mark = "OK" if c["ok"] else "FAIL"
        sys.stdout.write(f"  [{mark}] {c['name']}: {c['detail']}\n")
    if result["remediation"]:
        sys.stdout.write("Remediation:\n")
        for r in result["remediation"]:
            sys.stdout.write(f"  - {r}\n")
    sys.stdout.write(f"Known workspaces: {result['known_workspaces']}\n")
    return bool(result["ok"])


__all__ = [
    "workspace_root", "find_client_workspace", "get_client_db_path",
    "create_client_workspace", "open_client_workspace",
    "health_checks", "run_doctor", "diff_against",
]
