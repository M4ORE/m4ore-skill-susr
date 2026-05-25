# shared_kb/data — Bundled Knowledge Base (R3 placeholder)

This directory is intentionally **empty in R1**.  Round 3 will populate
it by porting select files from `skills/sustainability-report/references/`
into a tighter, version-stamped layout suited for snapshot copy into
per-client repos.

## Why empty now

CLAUDE.md §8 decision 3 — `shared_kb/` ships with the `pip install susr`
wheel (force-include rule in `packages/susr/pyproject.toml`).  Populating
it at R1 would force every subsequent KB edit through a full release
cycle; the decision is to scaffold the **mechanism** (this README,
`snapshot.py`, the import path) and fill the **content** at R3 after the
brain engine + MCP tools are working end-to-end.

## Expected R3 layout (from `docs/research/step1-spec.md §1.1`)

```
data/
  materiality-topics-universe.md
  ghg-protocol.md
  taiwan-fsc-sustainability-guidelines.md
  esg-glossary-zh-en.md
  compliance-checklist.md
  industry-packs/
    hotel.md
    textile.md
    electronics.md
    ...
```

Each file should carry a YAML frontmatter block compatible with
`susr.brain.entities` schemas (`regulation` / `framework` /
`emission_factor` / industry pack as plain markdown).

## How it gets into a client repo

`susr.shared_kb.snapshot.snapshot_into(client_repo_root)` copies the
entire `data/` tree into `<client>/shared/`.  See spec §1.1 layout +
§6.3 `create_client_workspace` MCP tool.
