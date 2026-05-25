"""Layer 1 lint tests: terminology consistency reverse-lookup.

Enforces docs/standards/skill-development.md §8.2:
  - 應用「範疇 1/2/3」而非「範圍 1/2/3」  → grep `範圍 [123]` 必須為零
  - 應用「利害關係人」而非「持份者」       → grep `持份者` 必須為零

esg-glossary-zh-en.md is excluded for references-level checks because a
bilingual glossary may need to mention the disallowed forms in order to
define / disambiguate them. SKILL.md gets a separate strict check.
"""

import re
from pathlib import Path


WRONG_SCOPE_RE = re.compile(r"範圍\s*[123]")
WRONG_STAKEHOLDER_RE = re.compile(r"持份者")

GLOSSARY_FILENAME = "esg-glossary-zh-en.md"


def _scan(text, pattern):
    """Return list of (line_number_1_based, line_text) for each match."""
    hits = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            hits.append((idx, line.rstrip()))
    return hits


def _format_hits(path, hits):
    return [f"{Path(path).name}:{lineno}: {text}" for lineno, text in hits]


# ---------------------------------------------------------------------------
# references/*.md (glossary excluded)
# ---------------------------------------------------------------------------


def test_no_wrong_scope_term(references_dir, read_md):
    ref_dir = Path(references_dir)
    md_files = sorted(
        p
        for p in ref_dir.glob("*.md")
        if p.name != GLOSSARY_FILENAME and p.name.lower() != "readme.md"
    )
    assert md_files, f"No reference .md files found under {ref_dir}"

    all_hits = []
    for md in md_files:
        hits = _scan(read_md(md), WRONG_SCOPE_RE)
        all_hits.extend(_format_hits(md, hits))

    assert all_hits == [], (
        "Found disallowed 「範圍 1/2/3」 (should be 「範疇 1/2/3」, §8.2):\n  - "
        + "\n  - ".join(all_hits)
    )


def test_no_wrong_stakeholder_term(references_dir, read_md):
    ref_dir = Path(references_dir)
    md_files = sorted(
        p
        for p in ref_dir.glob("*.md")
        if p.name != GLOSSARY_FILENAME and p.name.lower() != "readme.md"
    )
    assert md_files, f"No reference .md files found under {ref_dir}"

    all_hits = []
    for md in md_files:
        hits = _scan(read_md(md), WRONG_STAKEHOLDER_RE)
        all_hits.extend(_format_hits(md, hits))

    assert all_hits == [], (
        "Found disallowed 「持份者」 (should be 「利害關係人」, §8.2):\n  - "
        + "\n  - ".join(all_hits)
    )


# ---------------------------------------------------------------------------
# SKILL.md (no exclusions — must be strict)
# ---------------------------------------------------------------------------


def test_no_wrong_scope_term_in_skill(skill_dir, read_md):
    skill_md = Path(skill_dir) / "SKILL.md"
    assert skill_md.exists(), f"SKILL.md not found at {skill_md}"

    hits = _scan(read_md(skill_md), WRONG_SCOPE_RE)
    formatted = _format_hits(skill_md, hits)
    assert formatted == [], (
        "SKILL.md contains disallowed 「範圍 1/2/3」 "
        "(should be 「範疇 1/2/3」, §8.2):\n  - "
        + "\n  - ".join(formatted)
    )


def test_no_wrong_stakeholder_term_in_skill(skill_dir, read_md):
    skill_md = Path(skill_dir) / "SKILL.md"
    assert skill_md.exists(), f"SKILL.md not found at {skill_md}"

    hits = _scan(read_md(skill_md), WRONG_STAKEHOLDER_RE)
    formatted = _format_hits(skill_md, hits)
    assert formatted == [], (
        "SKILL.md contains disallowed 「持份者」 "
        "(should be 「利害關係人」, §8.2):\n  - "
        + "\n  - ".join(formatted)
    )
