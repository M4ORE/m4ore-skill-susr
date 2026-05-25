"""susr.shared_kb.snapshot — Snapshot the shipped KB into a client repo.

Plain file copy (not git submodule).  CLAUDE.md §8 decision 3:
"shared-kb 留在主 mono-repo 內，透過 snapshot copy 機制進 client repo".

Why not symlink:
    - Windows + git compatibility friction
    - 每個 client repo 自我完備（audit / reproducibility）
    - 顧問掌控升級節奏（環境部排放因子更新不會自動回溯）
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional

from susr.shared_kb import SHARED_KB_DATA_DIR


def _iter_files(root: Path):
    """Yield (relative_path, absolute_path) for every regular file under root."""
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path.relative_to(root), path


def _file_hash(path: Path) -> str:
    """SHA-256 of the file's bytes (for diff detection)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_into(
    client_repo_root: Path,
    *,
    subdir: str = "shared",
    overwrite: bool = False,
    source: Optional[Path] = None,
) -> dict:
    """Copy SHARED_KB_DATA_DIR into <client_repo_root>/<subdir>/.

    Returns {files_copied, files_skipped, target_path, source_version}.

    overwrite=False: refuses if target exists and is non-empty.
    overwrite=True : replaces target tree (used by update_shared_kb).

    `source` is an injection seam for tests; defaults to SHARED_KB_DATA_DIR.
    """
    src_root = Path(source) if source is not None else SHARED_KB_DATA_DIR
    target = Path(client_repo_root) / subdir

    if target.exists() and any(target.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"snapshot target {target} is non-empty; pass overwrite=True to replace"
            )
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for rel, abs_path in _iter_files(src_root):
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(abs_path, dst)
            copied += 1
        except OSError:  # pragma: no cover - rare permission edge
            skipped += 1

    return {
        "files_copied": copied,
        "files_skipped": skipped,
        "target_path": str(target),
        "source_version": get_shipped_version(),
    }


def diff_against(client_repo_root: Path, *, subdir: str = "shared") -> dict:
    """Compare client's shared/ snapshot against the currently shipped KB.

    Returns {added, removed, modified} file lists (str of relative paths).
    Used by update_shared_kb in dry-run mode.
    """
    src_root = SHARED_KB_DATA_DIR
    target = Path(client_repo_root) / subdir

    src_files = {str(rel): _file_hash(p) for rel, p in _iter_files(src_root)}
    dst_files = {str(rel): _file_hash(p) for rel, p in _iter_files(target)}

    added = sorted(set(src_files) - set(dst_files))
    removed = sorted(set(dst_files) - set(src_files))
    modified = sorted(
        rel for rel in set(src_files) & set(dst_files) if src_files[rel] != dst_files[rel]
    )

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "source_version": get_shipped_version(),
        "target_path": str(target),
    }


def apply_diff(
    client_repo_root: Path,
    *,
    subdir: str = "shared",
    accept_paths: Optional[list[str]] = None,
) -> dict:
    """套用 diff 到 client repo shared/.

    accept_paths=None  → 套用 diff 內所有 added + modified（不刪除 removed）。
    accept_paths=list  → 只套這些 relative path 的 added/modified；
                         removed 則一律不動（保留 client 端 audit trail）。

    Returns the same shape as diff_against() but trimmed to what was applied.
    """
    diff = diff_against(client_repo_root, subdir=subdir)
    candidates = set(diff["added"]) | set(diff["modified"])
    if accept_paths is not None:
        candidates &= set(accept_paths)

    src_root = SHARED_KB_DATA_DIR
    target = Path(client_repo_root) / subdir
    applied: list[str] = []
    for rel in sorted(candidates):
        src = src_root / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        applied.append(rel)

    return {
        "applied": applied,
        "skipped_removed": diff["removed"],
        "source_version": diff["source_version"],
        "target_path": str(target),
    }


def get_shipped_version() -> Optional[str]:
    """Read VERSION marker inside shared_kb/data/, fall back to package __version__.

    The VERSION file is a single-line semver string; absent means
    "use package version" so we never crash on a fresh checkout.
    """
    version_file = SHARED_KB_DATA_DIR / "VERSION"
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip() or None
        except OSError:  # pragma: no cover
            pass
    try:
        from susr import __version__

        return __version__
    except Exception:  # pragma: no cover
        return None


# Backward-compatible alias matching the prompt spec
snapshot_shared_kb_to = snapshot_into
diff_shared_kb = diff_against
update_shared_kb_in_client = apply_diff


__all__ = [
    "snapshot_into",
    "diff_against",
    "apply_diff",
    "get_shipped_version",
    "snapshot_shared_kb_to",
    "diff_shared_kb",
    "update_shared_kb_in_client",
]
