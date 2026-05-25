# packages/susr/tests — Layer 3 + Layer 4 Test Suite

Per CLAUDE.md §6.2, susr's five-layer test taxonomy splits geographically:

| Layer | Location | Lives in this dir? |
|-------|----------|---|
| 1 — static / lint | repo `tests/lint/` | no |
| 2 — SOP / scenario | repo `tests/scenarios/` | no |
| **3 — domain invariants** | **here** | **yes** |
| **4 — engine units** | **here** | **yes** |
| 5 — compliance regression | future | no |

## R1 status (this commit)

Scaffold only.  The fixtures in `conftest.py` (`PACKAGE_ROOT`, `ddl_path`,
`tmp_db_path`) are ready; no `test_*.py` files yet.  Adding tests before
the corresponding implementation exists would mean every test would
trivially `raise NotImplementedError` and provide no signal.

## R2 will add (per docs/research/step1-spec.md §8)

```
test_schema.py          # DDL v001 loads clean; schema_version=1
test_invariants.py      # I1..I5 — each with positive + negative cases
test_search_rrf.py      # RRF math pinned against known inputs
test_versions.py        # snapshot monotonic version_no + parent chain
test_timeline.py        # append-only triggers; restate threshold
test_embeddings.py      # Protocol conformance for each provider
test_mcp_handlers.py    # MCP tool input validation (pydantic)
test_pages.py           # CRUD round-trip
test_edges.py           # validate_edge accepts good, rejects bad
```

Each test file MUST pair with a CLAUDE.md §6.1 "feature claim" in
SKILL.md / CLAUDE.md / docs.  Tests are the forcing function against
the gbrain-style spec-impl gap (CLAUDE.md §6 commentary).

## Running

From repo root, with the workspace installed in editable mode:

```bash
uv sync
uv run pytest packages/susr/tests -v
```

Or, from inside `packages/susr/`:

```bash
pytest -v
```

## Fixture conventions

- Path fixtures are session-scoped and absolute (mirrors repo `conftest.py`).
- Per-test temp paths use pytest's `tmp_path`; never write under the
  package directory.
- BrainEngine fixtures (R2 addition) follow spec §8.1:

  ```python
  @pytest.fixture
  def tmp_brain(tmp_db_path):
      from susr import BrainEngine
      engine = BrainEngine.create_new(tmp_db_path, tenant_id=None,
                                       load_sqlite_vec=False)
      yield engine
      engine.close()
  ```

  `load_sqlite_vec=False` lets tests that don't touch vectors run on
  CI hosts where the wheel isn't installable.
