"""Layer 4 — shared_kb/data structural tests (Step 3 reference migration).

Asserts:
    - data/ directory exists and is non-empty after Step 3 migration
    - _manifest.yaml is loadable + has the expected shape
    - every path listed in manifest exists on disk
    - every .md under data/ (excluding README.md) is listed in manifest
      (catches orphan files left over from refactors)
    - every listed .md carries a YAML frontmatter block with the expected
      slug + category
    - snapshot.snapshot_into copies the full data/ tree into a target dir
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_frontmatter(path: Path) -> dict:
    """Return the YAML frontmatter dict at the top of a markdown file.

    Returns {} when the file has no frontmatter so callers can assert
    explicitly. Tolerates BOM + trailing whitespace.
    """
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    if not text.startswith("---"):
        return {}
    # split on the first two '---' boundaries
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm_block = parts[1]
    try:
        loaded = yaml.safe_load(fm_block) or {}
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _load_manifest(data_dir: Path) -> dict:
    manifest_path = data_dir / "_manifest.yaml"
    with manifest_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_shared_kb_data_dir_exists(shared_kb_data_dir: Path) -> None:
    """data/ directory must exist post-Step-3."""
    assert shared_kb_data_dir.is_dir(), (
        f"shared_kb/data/ missing: {shared_kb_data_dir}"
    )


def test_shared_kb_data_dir_non_empty(shared_kb_data_dir: Path) -> None:
    """At least the manifest + README + one knowledge file must be present."""
    md_files = list(shared_kb_data_dir.rglob("*.md"))
    assert len(md_files) >= 5, (
        f"expected at least 5 .md files under data/, got {len(md_files)}"
    )


def test_manifest_loadable(shared_kb_data_dir: Path) -> None:
    """_manifest.yaml parses + has required top-level keys."""
    manifest = _load_manifest(shared_kb_data_dir)
    assert isinstance(manifest, dict), "manifest must be a YAML mapping"
    assert "version" in manifest, "manifest missing top-level 'version'"
    assert "files" in manifest, "manifest missing top-level 'files'"
    assert isinstance(manifest["files"], list), "'files' must be a list"
    assert len(manifest["files"]) > 0, "'files' must list at least one entry"


def test_manifest_entries_have_required_fields(shared_kb_data_dir: Path) -> None:
    """Each manifest entry must have path / source / version / category / description."""
    manifest = _load_manifest(shared_kb_data_dir)
    required = {"path", "source", "version", "category", "description"}
    valid_categories = {
        "glossary",
        "framework",
        "factor",
        "regulation",
        "industry-pack",
        "checklist",
        "prompt",
    }
    for entry in manifest["files"]:
        missing = required - set(entry.keys())
        assert not missing, (
            f"manifest entry {entry.get('path', '<no path>')} missing fields: {missing}"
        )
        assert entry["category"] in valid_categories, (
            f"entry {entry['path']} has unknown category {entry['category']}"
        )


def test_manifest_paths_exist(shared_kb_data_dir: Path) -> None:
    """Every path listed in manifest exists on disk."""
    manifest = _load_manifest(shared_kb_data_dir)
    missing: list[str] = []
    for entry in manifest["files"]:
        rel = entry["path"]
        if not (shared_kb_data_dir / rel).is_file():
            missing.append(rel)
    assert not missing, f"manifest references non-existent files: {missing}"


def test_no_orphan_files(shared_kb_data_dir: Path) -> None:
    """Every .md under data/ (except README.md) is listed in the manifest.

    Guards against refactors that leave stale files behind.  Frontmatter-bearing
    knowledge files MUST be tracked centrally so snapshot consumers (and audit
    tooling) can enumerate the KB deterministically.
    """
    manifest = _load_manifest(shared_kb_data_dir)
    listed = {entry["path"].replace("\\", "/") for entry in manifest["files"]}

    on_disk: set[str] = set()
    for md in shared_kb_data_dir.rglob("*.md"):
        rel = md.relative_to(shared_kb_data_dir).as_posix()
        if rel == "README.md":
            continue
        on_disk.add(rel)

    orphans = on_disk - listed
    assert not orphans, (
        f"the following .md files are on disk but NOT in _manifest.yaml: {sorted(orphans)}"
    )


def test_each_md_has_frontmatter(shared_kb_data_dir: Path) -> None:
    """Every listed .md carries YAML frontmatter with slug + category."""
    manifest = _load_manifest(shared_kb_data_dir)
    for entry in manifest["files"]:
        path = shared_kb_data_dir / entry["path"]
        fm = _read_frontmatter(path)
        assert fm, f"{entry['path']} missing frontmatter block"
        assert "slug" in fm, f"{entry['path']} frontmatter missing 'slug'"
        assert "category" in fm, f"{entry['path']} frontmatter missing 'category'"
        assert fm["category"] == entry["category"], (
            f"{entry['path']} frontmatter category={fm['category']} "
            f"does not match manifest category={entry['category']}"
        )


def test_frontmatter_sources_point_back_to_references(
    shared_kb_data_dir: Path,
) -> None:
    """Each file's frontmatter 'source' field traces back to a real
    skills/sustainability-report/references/ file in the same repo."""
    manifest = _load_manifest(shared_kb_data_dir)
    # data_dir = packages/susr/susr/shared_kb/data -> repo root is 5 levels up
    repo_root = shared_kb_data_dir.parents[4]
    for entry in manifest["files"]:
        path = shared_kb_data_dir / entry["path"]
        fm = _read_frontmatter(path)
        src_rel = fm.get("source")
        assert src_rel, f"{entry['path']} frontmatter missing 'source'"
        assert src_rel.startswith("skills/sustainability-report/references/"), (
            f"{entry['path']} source must point under skills/..../references/, "
            f"got {src_rel}"
        )
        assert (repo_root / src_rel).is_file(), (
            f"{entry['path']} source file {src_rel} not found at repo root "
            f"{repo_root}"
        )


# ---------------------------------------------------------------------------
# Snapshot integration
# ---------------------------------------------------------------------------


def test_snapshot_copies_kb(tmp_path: Path, shared_kb_data_dir: Path) -> None:
    """snapshot_into() copies the entire data/ tree into <target>/shared/.

    Verifies the snapshot mechanism end-to-end against the populated KB
    so future tree changes are exercised by CI on every commit.
    """
    from susr.shared_kb.snapshot import snapshot_into

    result = snapshot_into(tmp_path, overwrite=False)

    # Count source .md files (excluding YAML manifest, but including it as a
    # regular file because snapshot_into copies *all* regular files).
    src_files = [p for p in shared_kb_data_dir.rglob("*") if p.is_file()]
    assert result["files_copied"] == len(src_files), (
        f"expected {len(src_files)} files copied, got {result['files_copied']}"
    )
    assert result["files_skipped"] == 0

    target = Path(result["target_path"])
    assert target.is_dir()
    # spot-check: the manifest itself made the trip
    assert (target / "_manifest.yaml").is_file()
    # spot-check: a deep file made the trip
    assert (target / "prompts" / "phase4-xlsx.md").is_file()


def test_snapshot_refuses_non_empty_target_without_overwrite(
    tmp_path: Path,
) -> None:
    """snapshot_into refuses to clobber a non-empty target by default."""
    from susr.shared_kb.snapshot import snapshot_into

    # Seed the target with something
    target_parent = tmp_path
    (target_parent / "shared").mkdir()
    (target_parent / "shared" / "leftover.txt").write_text("dont touch me")

    with pytest.raises(FileExistsError):
        snapshot_into(target_parent, overwrite=False)

    # overwrite=True clears + copies
    result = snapshot_into(target_parent, overwrite=True)
    assert result["files_copied"] > 0
    # leftover gone
    assert not (target_parent / "shared" / "leftover.txt").exists()
