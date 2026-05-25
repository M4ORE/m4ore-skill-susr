# susr — Sustainability/ESG Report Co-pilot Brain

Local-first, MCP-native package for ESG consultants.  Single-file SQLite
(via `sqlite-vec` + FTS5) holds the consultant's "second brain" for one
or many client engagements; Claude Desktop is the chat-driven GUI.

> **Status (2026-05-25):** Step 1 Round 1 — scaffold + DDL only.
> Round 2 fills the engine implementation; Round 3 ports the shared
> knowledge base into `susr/shared_kb/data/`.

## Install (planned UX — R2+)

```bash
pip install "susr[embeddings-bge]"
susr-mcp doctor                     # one-time health check
# wire ~/.../claude_desktop_config.json → command: "susr-mcp"
```

Default embedding provider is local BGE-M3 (1024d) — no client data
leaves the consultant's machine.  Spec §5 covers `local` / `cloud` /
`twostage` policy selection per client.

## Module map

| Path | Responsibility |
|------|----------------|
| `susr/brain/engine.py` | `BrainEngine` façade over SQLite |
| `susr/brain/ddl/v001_init.sql` | Complete, runnable schema |
| `susr/brain/migrations.py` | DDL loader + schema version |
| `susr/brain/entities.py` | 17 ESG entity types + Pydantic schemas |
| `susr/brain/edges.py` | 19 typed-edge registry + `validate_edge` |
| `susr/brain/invariants.py` | 5 connectivity invariants (fail-closed) |
| `susr/brain/search.py` | Hybrid vector + FTS5 retrieval with RRF (k=60) |
| `susr/brain/pages.py` | page CRUD (markdown ↔ DB) |
| `susr/brain/timeline.py` | Append-only timeline_entries |
| `susr/brain/versions.py` | `page_versions` snapshot/restore |
| `susr/embeddings/provider.py` | `EmbeddingProvider` Protocol |
| `susr/embeddings/bge_m3.py` | BGE-M3 local (DEFAULT) |
| `susr/embeddings/qwen3.py` | Qwen3 local (backup) |
| `susr/embeddings/openai.py` | OpenAI cloud (fallback) |
| `susr/llm/provider.py` | `LLMProvider` Protocol |
| `susr/llm/anthropic.py` | Anthropic provider |
| `susr/mcp/__main__.py` | `susr-mcp` console-script entry |
| `susr/mcp/server.py` | FastMCP singleton + tool wiring |
| `susr/mcp/tools/phase3.py` | 4 Phase-3 materiality tools |
| `susr/mcp/tools/workspace.py` | 4 workspace ops (create / health / KB / promote) |
| `susr/shared_kb/snapshot.py` | Snapshot copy bundled KB into client repos |
| `susr/workspace.py` | Per-client workspace lifecycle (shared logic) |

## Design docs

Authoritative design lives one directory up:

- `../../CLAUDE.md` — repo-wide rules, especially §8 (engineering decisions)
- `../../docs/research/step1-spec.md` — the full Step 1 spec (architecture, DDL, tools)
- `../../docs/defeinition.md` / `target.md` / `product_structure.md` — three-principle constitution
- `../../docs/user-guide/` — consultant-facing guides (TL;DR-first, see CLAUDE.md §4.6.5)

## Engineering decisions (locked, see CLAUDE.md §8)

- Python 3.11 + uv workspace
- SQLite + sqlite-vec + FTS5 (no Postgres)
- Single Python package (no brain / mcp / cli split)
- `shared_kb` ships inside the wheel
- Only console script is `susr-mcp` (no `susr` CLI subcommands)
- MVP scope = Phase 3 materiality assessment, end-to-end
- LLM + embedding both day-1 abstracted behind a Protocol
- `tenant_id` + `xbrl_concept` columns reserved (nullable) for future use

## Tests

- Layer 1 + 2 (lint, scenario) live at repo root `tests/`
- Layer 3 + 4 (domain invariants, engine units) live in `packages/susr/tests/`
- Run `uv run pytest packages/susr/tests -v` once R2 lands the test files

## License

MIT — see repo `LICENSE`.
