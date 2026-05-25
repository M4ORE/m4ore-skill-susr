"""Layer 1 lint tests: structural checks for references/ and SKILL.md.

Enforces docs/standards/skill-development.md §8.1 (fixed-position usage
timing line) and frontmatter conventions.
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# references/*.md structural checks
# ---------------------------------------------------------------------------


def test_each_reference_has_usage_timing(references_dir, read_md):
    """§8.1: line 3 of every references/*.md must start with `**使用時機**`.

    Layout assumed: line 1 = `# heading`, line 2 = blank, line 3 = usage timing.
    README.md (if present) is excluded since it is a directory index, not a
    reference document.
    """
    ref_dir = Path(references_dir)
    md_files = sorted(
        p for p in ref_dir.glob("*.md") if p.name.lower() != "readme.md"
    )
    assert md_files, f"No reference .md files found under {ref_dir}"

    failures = []
    for md in md_files:
        lines = read_md(md).splitlines()
        if len(lines) < 3:
            failures.append(
                f"{md.name}: file has only {len(lines)} line(s), "
                f"cannot contain a usage-timing line at line 3"
            )
            continue
        third = lines[2]
        if not third.startswith("**使用時機**"):
            failures.append(
                f"{md.name}: line 3 should start with `**使用時機**`, "
                f"got: {third!r}"
            )

    assert failures == [], (
        "References missing well-formed usage-timing line (§8.1):\n  - "
        + "\n  - ".join(failures)
    )


# ---------------------------------------------------------------------------
# SKILL.md frontmatter checks
# ---------------------------------------------------------------------------


def test_skill_md_has_frontmatter(skill_dir, read_md, parse_frontmatter):
    skill_md = Path(skill_dir) / "SKILL.md"
    assert skill_md.exists(), f"SKILL.md not found at {skill_md}"

    fm = parse_frontmatter(read_md(skill_md))
    assert fm is not None, f"SKILL.md at {skill_md} has no YAML frontmatter"
    assert isinstance(fm, dict), (
        f"SKILL.md frontmatter should parse to a mapping, got {type(fm).__name__}"
    )

    missing = [key for key in ("name", "description") if key not in fm]
    assert missing == [], (
        f"SKILL.md frontmatter is missing required field(s): {missing}"
    )


def test_skill_md_name_matches_folder(skill_dir, read_md, parse_frontmatter):
    skill_md = Path(skill_dir) / "SKILL.md"
    fm = parse_frontmatter(read_md(skill_md))
    assert fm is not None, f"SKILL.md at {skill_md} has no YAML frontmatter"

    folder_name = Path(skill_dir).name
    actual = fm.get("name")
    assert actual == folder_name, (
        f"SKILL.md frontmatter `name` should match folder name "
        f"({folder_name!r}), got {actual!r}"
    )
    # Belt-and-braces: encode the expected value explicitly per task spec.
    assert actual == "sustainability-report", (
        f"SKILL.md frontmatter `name` should be 'sustainability-report', "
        f"got {actual!r}"
    )


# ---------------------------------------------------------------------------
# Repo-level principle docs (CLAUDE.md §0)
# ---------------------------------------------------------------------------


def test_principle_docs_exist(REPO_ROOT):
    repo = Path(REPO_ROOT)
    expected = [
        repo / "docs" / "defeinition.md",
        repo / "docs" / "target.md",
        repo / "docs" / "product_structure.md",
    ]
    missing = [str(p.relative_to(repo)) for p in expected if not p.exists()]
    assert missing == [], (
        f"Required principle docs missing (CLAUDE.md §0): {missing}"
    )


def test_claude_md_exists(REPO_ROOT):
    claude_md = Path(REPO_ROOT) / "CLAUDE.md"
    assert claude_md.exists(), f"CLAUDE.md not found at {claude_md}"
