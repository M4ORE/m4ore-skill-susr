"""susr.brain.entities — 17 ESG entity types + frontmatter schemas.

Each entity_type is a markdown file under a per-client repo with a YAML
frontmatter dict that satisfies a Pydantic schema declared here.  The
frontmatter is then flattened into entity_attributes for query.

The 17 types come from gbrain-survey §4.1 and were locked at
docs/research/step1-spec.md §2.3.  Path conventions there.

R1: enum + ENTITY_SCHEMAS map + per-entity model stubs.
R2: fill each model with the required + optional fields from spec §2.3 table.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, Field, ValidationError


# ---------------------------------------------------------------------------
# 17 ESG entity types (literal enum + tuple for runtime iteration).
# Order mirrors spec §2.3 table.
# ---------------------------------------------------------------------------

EntityType = Literal[
    "client",
    "report",
    "chapter",
    "topic",
    "iro",
    "stakeholder",
    "engagement",
    "governance",
    "action",
    "target",
    "kpi",
    "datapoint",
    "regulation",
    "emission_factor",
    "framework",
    "peer_company",
    "source_doc",
]

ENTITY_TYPES: tuple[str, ...] = (
    "client",
    "report",
    "chapter",
    "topic",
    "iro",
    "stakeholder",
    "engagement",
    "governance",
    "action",
    "target",
    "kpi",
    "datapoint",
    "regulation",
    "emission_factor",
    "framework",
    "peer_company",
    "source_doc",
)
assert len(ENTITY_TYPES) == 17, "ENTITY_TYPES drifted from spec §2.3 (17 types)"


# ---------------------------------------------------------------------------
# Per-entity Pydantic frontmatter schemas.
# Each one mirrors a row of spec §2.3 table.
# R2 expands required vs. optional fields with proper validators.
# ---------------------------------------------------------------------------


class _EntityBase(BaseModel):
    """Common slug field shared by every entity."""

    slug: str
    # Reserved for iXBRL/ESEF future (CLAUDE.md §8 Q16).  Nullable + unused in R1.
    xbrl_concept: Optional[str] = None


class ClientFrontmatter(_EntityBase):
    """`_client.md`. Spec §2.3 row 1."""

    legal_name: str
    stock_code: Optional[str] = None
    industry_gri_sector: str
    boundary: Literal["合併", "營運控制", "股權法"]
    reporting_period: str
    applicable_standards: Sequence[str]
    embedding_policy: Optional[Literal["local", "cloud", "twostage"]] = "twostage"


class ReportFrontmatter(_EntityBase):
    """`projects/<year>-sr/_project.md`. Spec §2.3 row 2."""

    client_slug: str
    year: int
    version: str
    language: str
    framework_bundle: Sequence[str]
    status: str


class ChapterFrontmatter(_EntityBase):
    """Spec §2.3 row 3."""

    report_slug: str
    title: str
    framework_refs: Sequence[str]
    owner: str


class TopicFrontmatter(_EntityBase):
    """Spec §2.3 row 4 — the centerpiece of MVP Phase 3."""

    name: str
    axis: Literal["E", "S", "G"]
    impact_score: float = Field(ge=0, le=5)
    financial_score: float = Field(ge=0, le=5)
    materiality_tier: Literal["核心", "重大", "邊界"]
    industry_specificity: Optional[str] = None
    assessed_at: Optional[str] = None
    assessed_by: Optional[str] = None
    assessment_year: Optional[int] = None


class IroFrontmatter(_EntityBase):
    """Spec §2.3 row 5."""

    topic_slug: str
    type: Literal["Impact", "Risk", "Opportunity"]
    category: str
    time_horizon: Literal["S", "M", "L"]
    financial_magnitude: float


class StakeholderFrontmatter(_EntityBase):
    """Spec §2.3 row 6."""

    category: str
    influence_on_company: float
    affected_by_company: float


class EngagementFrontmatter(_EntityBase):
    """Spec §2.3 row 7."""

    stakeholder_slug: str
    topic_slugs: Sequence[str]
    date: str
    method: str
    sample_size: Optional[int] = None
    findings_summary: str


class GovernanceFrontmatter(_EntityBase):
    """Spec §2.3 row 8."""

    body: str
    oversight_topics: Sequence[str]
    meeting_frequency: str
    kpi_linkage: Sequence[str]


class ActionFrontmatter(_EntityBase):
    """Spec §2.3 row 9."""

    chapter_slug: str
    iro_addressed: Sequence[str]
    budget: float
    progress_pct: float
    owner_department: str
    period: str


class TargetFrontmatter(_EntityBase):
    """Spec §2.3 row 10 — invariant I3 enforces all 4 fields below."""

    kpi_slug: str
    baseline_year: int
    baseline_value: float
    target_value: float
    target_year: int
    verification_path: str


class KpiFrontmatter(_EntityBase):
    """Spec §2.3 row 11."""

    topic_slug: str
    name: str
    unit: str
    framework_refs: Sequence[str]
    boundary: str
    formula: str


class DatapointFrontmatter(_EntityBase):
    """Spec §2.3 row 12 — most heavily linked entity in Phase 4."""

    kpi_slug: str
    year: int
    value: float
    source_refs: Sequence[str]
    calculation_method: str
    assurance_status: str
    last_assessed: str
    responsible_person: str


class RegulationFrontmatter(_EntityBase):
    """Spec §2.3 row 13 — typically in shared_kb, not per-client."""

    jurisdiction: str
    authority: str
    version: str
    effective_from: str
    effective_to: Optional[str] = None
    applies_to_industries: Sequence[str]


class EmissionFactorFrontmatter(_EntityBase):
    """Spec §2.3 row 14 — typically in shared_kb, used by GHG datapoints."""

    category: str
    region: str
    source: str
    version: str
    value: float
    unit: str
    effective_from: str


class FrameworkFrontmatter(_EntityBase):
    """Spec §2.3 row 15."""

    version: str
    disclosures: Sequence[str]
    is_mandatory_in: Sequence[str]


class PeerCompanyFrontmatter(_EntityBase):
    """Spec §2.3 row 16."""

    industry: str
    country: str
    latest_report_year: int
    notable_practices: Sequence[str]


class SourceDocFrontmatter(_EntityBase):
    """Spec §2.3 row 17."""

    client_slug: str
    doc_type: str
    period: str
    file_hash: str
    ingest_date: str


# ---------------------------------------------------------------------------
# Schema registry — single lookup for "which Pydantic model validates this
# entity_type?"
# ---------------------------------------------------------------------------

ENTITY_SCHEMAS: dict[str, type[BaseModel]] = {
    "client": ClientFrontmatter,
    "report": ReportFrontmatter,
    "chapter": ChapterFrontmatter,
    "topic": TopicFrontmatter,
    "iro": IroFrontmatter,
    "stakeholder": StakeholderFrontmatter,
    "engagement": EngagementFrontmatter,
    "governance": GovernanceFrontmatter,
    "action": ActionFrontmatter,
    "target": TargetFrontmatter,
    "kpi": KpiFrontmatter,
    "datapoint": DatapointFrontmatter,
    "regulation": RegulationFrontmatter,
    "emission_factor": EmissionFactorFrontmatter,
    "framework": FrameworkFrontmatter,
    "peer_company": PeerCompanyFrontmatter,
    "source_doc": SourceDocFrontmatter,
}
assert set(ENTITY_SCHEMAS.keys()) == set(ENTITY_TYPES), \
    "ENTITY_SCHEMAS drifted from ENTITY_TYPES — keep them in lock-step"


def validate_frontmatter(entity_type: str, payload: dict[str, Any]) -> BaseModel:
    """驗證原始 YAML frontmatter，回傳解析後的 Pydantic 物件。

    Raises:
        KeyError: ``entity_type`` 不在 ENTITY_SCHEMAS。
        pydantic.ValidationError: 必填欄位缺失 / 型別不符。
    """
    if entity_type not in ENTITY_SCHEMAS:
        raise KeyError(
            f"unknown entity_type {entity_type!r}; expected one of {sorted(ENTITY_SCHEMAS)}"
        )
    schema_cls = ENTITY_SCHEMAS[entity_type]
    return schema_cls.model_validate(payload)


# ---------------------------------------------------------------------------
# Frontmatter ↔ dict helpers
#
# brain.pages stores frontmatter via the entity_attributes table, but MCP
# tools and tests round-trip the same data as plain dicts.  These helpers
# centralise the boundary so we keep one definition of "what counts as the
# canonical frontmatter dict".
# ---------------------------------------------------------------------------


def entity_to_frontmatter(entity: BaseModel) -> dict[str, Any]:
    """Pydantic entity → plain frontmatter dict (excludes unset None fields).

    ``mode='json'`` ensures things like dates / sets serialize to YAML-safe
    primitives.  We exclude ``None`` values that are merely defaults so the
    on-disk YAML stays small.
    """
    return entity.model_dump(mode="json", exclude_none=True)


def frontmatter_to_entity(entity_type: str, frontmatter: dict[str, Any]) -> BaseModel:
    """plain dict → 對應 entity 的 Pydantic 物件（等同 validate_frontmatter 別名）。

    Provided as a named pair to ``entity_to_frontmatter`` for callers who
    prefer the round-trip symmetry; behaviour is identical.
    """
    return validate_frontmatter(entity_type, frontmatter)


__all__ = [
    "EntityType",
    "ENTITY_TYPES",
    "ENTITY_SCHEMAS",
    "ClientFrontmatter",
    "ReportFrontmatter",
    "ChapterFrontmatter",
    "TopicFrontmatter",
    "IroFrontmatter",
    "StakeholderFrontmatter",
    "EngagementFrontmatter",
    "GovernanceFrontmatter",
    "ActionFrontmatter",
    "TargetFrontmatter",
    "KpiFrontmatter",
    "DatapointFrontmatter",
    "RegulationFrontmatter",
    "EmissionFactorFrontmatter",
    "FrameworkFrontmatter",
    "PeerCompanyFrontmatter",
    "SourceDocFrontmatter",
    "validate_frontmatter",
    "entity_to_frontmatter",
    "frontmatter_to_entity",
    "ValidationError",
]
