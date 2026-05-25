"""susr — Sustainability/ESG report Co-pilot brain for consultants.

Local-first, MCP-native package. Single-file SQLite (sqlite-vec + FTS5)
holds 17 ESG entities, 19 typed edges, hybrid retrieval via RRF, and
append-only timeline + page_versions for anti-greenwashing evidence chain.

Public surface (re-exported here for the common ergonomic):
    BrainEngine      — orchestration façade over the SQLite brain
    SearchResult     — return shape of hybrid_search
    hybrid_search    — vector + FTS5 fused retrieval
    EntityType       — Literal type of the 17 supported ESG entities
    EDGE_REGISTRY    — typed-edge registry (19 entries)

Heavier modules (mcp, embeddings, llm) intentionally NOT imported at
package load — they pull in optional deps (mcp[cli], sentence-transformers,
anthropic) and we want `import susr` to stay cheap.

See:
    docs/research/step1-spec.md  — full design spec
    CLAUDE.md §8                  — locked engineering decisions
"""

from __future__ import annotations

__version__ = "0.1.0"

# Lazy public re-exports — keep import-time cost low.
# Consumers do `from susr import BrainEngine` and only then pay for brain init.
from susr.brain.engine import BrainEngine
from susr.brain.entities import ENTITY_TYPES, EntityType
from susr.brain.edges import EDGE_REGISTRY
from susr.brain.search import SearchResult, hybrid_search

__all__ = [
    "__version__",
    "BrainEngine",
    "ENTITY_TYPES",
    "EntityType",
    "EDGE_REGISTRY",
    "SearchResult",
    "hybrid_search",
]
