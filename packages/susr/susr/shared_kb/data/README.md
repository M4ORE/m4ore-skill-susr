# shared_kb/data — Bundled Knowledge Base

This directory ships inside the `susr` wheel (force-included via
`packages/susr/pyproject.toml`) so a fresh `pip install susr` carries the
full cross-client ESG KB.  CLAUDE.md §8 decision 3 — `snapshot_into()`
copies this entire tree into each client repo's `shared/` directory at
`create_client_workspace` time.

## Layout

```
data/
├── README.md                            ← this file
├── _manifest.yaml                       ← machine-readable index of every file
├── glossary/
│   └── esg-zh-en.md                     ← zh-Hant / EN ESG terminology
├── frameworks/                          ← (placeholder; see _manifest.yaml notes)
├── factors/
│   └── ghg-protocol-overview.md         ← GHG Protocol calc principles + TW power factor
├── regulations/
│   └── taiwan-fsc-sustainability-guidelines.md
├── industry-packs/
│   └── _universe.md                     ← materiality topics universe (E12+S14+G10+EC4)
├── checklists/
│   ├── compliance-phase7.md             ← Phase 7 final-review checklist
│   └── websearch-pending.md             ← Phase 2 outstanding-research tracker
└── prompts/
    ├── phase2-research.md
    ├── phase4-xlsx.md
    ├── phase6-docx.md
    ├── phase6-pdf.md
    └── phase6-pptx.md
```

`frameworks/` ships empty deliberately — the GRI / ISSB / TCFD spec text
in the source references lives inside `checklists/compliance-phase7.md`
(§F + §G) and `glossary/esg-zh-en.md`.  Splitting it would either
duplicate content or fragment it below the "保真" threshold.  See
`_manifest.yaml` bottom comment for the follow-up list.

## Source

Every file traces back to `skills/sustainability-report/references/*.md`
in this mono-repo.  The skill path remains operational for the Claude
Code chat workflow (CLAUDE.md §8 decision 5 — Skill and Brain run in
parallel, independent).  This `data/` tree is the **packaged copy** used
by the MCP / brain workflow inside Claude Desktop / Cursor / Windsurf.

Each markdown file carries a YAML frontmatter block:

```yaml
---
slug: <stable identifier>
category: glossary | framework | factor | regulation | industry-pack | checklist | prompt
source: skills/sustainability-report/references/<original>.md
version: "YYYY-MM-DD"
language: zh-Hant
last_reviewed: YYYY-MM-DD
---
```

`_manifest.yaml` is the canonical index; tests in
`tests/test_shared_kb.py` enforce path-listed parity (no orphan files,
every listed path exists, every file has a parseable frontmatter).

## Versioning

The whole tree carries a single content-version stamp (top of
`_manifest.yaml`).  When a per-client snapshot diverges
(`snapshot.diff_against`), the diff is reported against this stamp.  A
client never auto-upgrades — `apply_diff()` requires the consultant to
opt-in, which preserves prior-year emission-factor traceability (CLAUDE.md
§8 decision 3 — "顧問掌控升級節奏").

## How it gets into a client repo

```python
from pathlib import Path
from susr.shared_kb.snapshot import snapshot_into

snapshot_into(Path("~/work/lealea-5364").expanduser())
# -> writes a frozen copy into ~/work/lealea-5364/shared/
```

See `susr/shared_kb/snapshot.py` for the full API
(`snapshot_into` / `diff_against` / `apply_diff` / `get_shipped_version`).
