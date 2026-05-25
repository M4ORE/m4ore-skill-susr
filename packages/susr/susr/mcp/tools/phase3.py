"""susr.mcp.tools.phase3 — 4 Phase-3 materiality assessment tools.

These are the MVP v0.1 deliverable: the consultant runs end-to-end
materiality assessment for a client (lealea-5364 fixture) by chatting
with Claude Desktop, which calls these tools.

Tools (spec §6.2):
    search_topics_universe         — pull candidate topics from shared_kb + client
    score_topic_dual_axis          — write impact + financial scores → tier
    generate_materiality_matrix    — render matrix .md + .svg, run invariants
    stakeholder_engagement_helper  — record an engagement event + links

Tool functions are NOT decorated here in R1 (would require importing the
FastMCP singleton and triggering registration side-effects).  R2 will
add the @mcp.tool() decorators once susr.mcp.server is implemented.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tool 1: search_topics_universe
# ---------------------------------------------------------------------------


class TopicCandidate(BaseModel):
    """One row returned by search_topics_universe."""

    slug: str
    name: str
    axis: Literal["E", "S", "G"]
    industry_specificity: Optional[str] = None
    source_kb: Literal["shared", "client"]


def search_topics_universe(
    industry: str,
    framework: Literal["GRI", "ISSB", "ESRS", "TW_FSC", "SASB"] = "GRI",
    client_slug: Optional[str] = None,
    top_k: int = 40,
) -> list[TopicCandidate]:
    """Phase 3 step 1 — pull candidate topics for the consultant to review.

    Merges three sources:
        - shared_kb/industry-packs/<industry>.md   (cross-client baseline)
        - framework standard topic universe        (GRI sector / ISSB ind.)
        - client.entities/topics/*                 (already-imported topics)

    Returns top_k de-duplicated candidates with axis + provenance.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.2 tool 1")


# ---------------------------------------------------------------------------
# Tool 2: score_topic_dual_axis
# ---------------------------------------------------------------------------


class ImpactScores(BaseModel):
    """Four-axis impact assessment per the dual-materiality method."""

    severity: float = Field(ge=1, le=5)
    scope: float = Field(ge=1, le=5)
    irreversibility: float = Field(ge=1, le=5)
    likelihood: float = Field(ge=1, le=5)


class FinancialScores(BaseModel):
    """Financial materiality assessment."""

    magnitude: float = Field(ge=1, le=5)
    time_horizon: Literal["S", "M", "L"]
    probability: float = Field(ge=1, le=5)


class TopicScoreResult(BaseModel):
    """Outcome of score_topic_dual_axis."""

    topic_slug: str
    impact_score: float
    financial_score: float
    materiality_tier: Literal["核心", "重大", "邊界"]
    page_file: str
    timeline_entry_id: int


def score_topic_dual_axis(
    client_slug: str,
    topic_slug: str,
    impact: ImpactScores,
    financial: FinancialScores,
    actor: str,
    rationale: Optional[str] = None,
) -> TopicScoreResult:
    """Phase 3 step 2 — write dual-axis scores onto a topic.

    Normalizes the input axes to 1–5, computes:
        impact_score    = mean(severity, scope, irreversibility, likelihood)
        financial_score = mean(magnitude, probability) with time_horizon stored
    Tier rule (spec §6.2): impact >= 4 AND financial >= 4 → 核心;
        any >= 3.5 → 重大; else 邊界.

    Side-effects: updates entities/topics/<topic_slug>.md frontmatter,
    appends timeline_entries(action_type='verify', payload={raw_scores}).
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.2 tool 2")


# ---------------------------------------------------------------------------
# Tool 3: generate_materiality_matrix
# ---------------------------------------------------------------------------


class MaterialityMatrix(BaseModel):
    """Outcome of generate_materiality_matrix."""

    matrix_md_path: str
    matrix_svg_path: str
    core_topics: list[str]
    material_topics: list[str]
    border_topics: list[str]
    invariants_passed: bool
    invariant_violations: list[str] = []


def generate_materiality_matrix(
    client_slug: str,
    year: int,
    include_svg: bool = True,
) -> MaterialityMatrix:
    """Phase 3 step 3 — render the matrix + run I1/I2 invariants.

    Reads all scored topics, produces materiality-YYYY.md + optional SVG
    grid (mirror of examples/lealea-5364/phase3-materiality.md §5 layout),
    runs invariants (core topics MUST chain to actions), writes a
    page_versions snapshot with snapshot_reason='phase_complete'.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.2 tool 3")


# ---------------------------------------------------------------------------
# Tool 4: stakeholder_engagement_helper
# ---------------------------------------------------------------------------


class EngagementRecord(BaseModel):
    """Outcome of stakeholder_engagement_helper."""

    engagement_slug: str
    page_file: str
    topics_raised: list[str]
    timeline_entry_id: int


def stakeholder_engagement_helper(
    client_slug: str,
    stakeholder_slug: str,
    method: Literal["問卷", "訪談", "焦點", "說明會"],
    date: str,
    sample_size: Optional[int],
    topics_raised: list[str],
    findings_summary: str,
    evidence_refs: Optional[list[str]] = None,
    actor: str = "consultant",
) -> EngagementRecord:
    """Phase 3 step 4 — record one stakeholder engagement event.

    Creates entities/stakeholders/<x>/engagements/<date>.md (entity_type='engagement'),
    auto-creates:
        - stakeholder_engaged_via   (stakeholder → engagement)
        - engagement_raised_topic   (engagement → each topic_raised)
        - topic_identified_by       (each topic → stakeholder)  [back-link for §2.5]
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §6.2 tool 4")
