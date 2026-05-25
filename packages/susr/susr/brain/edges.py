"""susr.brain.edges — 19 typed edges registry + validation.

Every link row in the DB has an edge_type drawn from EDGE_REGISTRY here.
Validation rejects (a) unknown edge_types and (b) src→dst entity_type
mismatches.  The registry lives in code, not SQL CHECK, so adding a new
edge type only requires a Python change (no ALTER TABLE).

The 19 edges come from gbrain-survey §4.2 and were locked at
docs/research/step1-spec.md §2.4.

R1: registry literal + validate_edge signature.
R2: implement validate_edge + supply EDGE_DOCS for tooltips.
"""

from __future__ import annotations

from typing import NamedTuple

from susr.brain.entities import EntityType


class EdgeSpec(NamedTuple):
    """Schema entry for one typed edge.

    Attributes:
        src: required entity_type on the source side
        dst: required entity_type on the destination side
        description: short human-readable description (for tooltips / errors)
    """

    src: str  # EntityType, but using str so the NamedTuple stays JSON-friendly
    dst: str
    description: str


# Edge registry — 19 entries, ordered to match spec §2.4 table.
EDGE_REGISTRY: dict[str, EdgeSpec] = {
    "has_report":                          EdgeSpec("client",       "report",          "Client owns Report"),
    "contains_chapter":                    EdgeSpec("report",       "chapter",         "Report contains Chapter"),
    "discloses_topic":                     EdgeSpec("chapter",      "topic",           "Chapter discloses Topic"),
    "topic_identified_by":                 EdgeSpec("topic",        "stakeholder",     "Topic identified through Stakeholder engagement"),
    "topic_has_iro":                       EdgeSpec("topic",        "iro",             "Topic decomposed into Impact/Risk/Opportunity"),
    "iro_addressed_by":                    EdgeSpec("iro",          "action",          "IRO addressed by Action"),
    "action_tracks":                       EdgeSpec("action",       "target",          "Action tracked against Target"),
    "target_measures":                     EdgeSpec("target",       "kpi",             "Target measured by KPI"),
    "kpi_reported_as":                     EdgeSpec("kpi",          "datapoint",       "KPI reported as yearly DataPoint"),
    "datapoint_derived_from":              EdgeSpec("datapoint",    "source_doc",      "DataPoint derived from a SourceDoc (traceability)"),
    "datapoint_calculated_with":           EdgeSpec("datapoint",    "emission_factor", "DataPoint calculated using an EmissionFactor (GHG)"),
    "datapoint_restated_from":             EdgeSpec("datapoint",    "datapoint",       "DataPoint restated from a prior-year DataPoint (>5% delta)"),
    "governance_oversees":                 EdgeSpec("governance",   "topic",           "Governance body oversees Topic"),
    "governance_reviews":                  EdgeSpec("governance",   "target",          "Governance body reviews Target"),
    "chapter_conforms_to":                 EdgeSpec("chapter",      "framework",       "Chapter conforms to Framework standard"),
    "regulation_requires_disclosure_of":   EdgeSpec("regulation",   "topic",           "Regulation requires disclosure of Topic"),
    "stakeholder_engaged_via":             EdgeSpec("stakeholder",  "engagement",      "Stakeholder engaged via an Engagement event"),
    "engagement_raised_topic":             EdgeSpec("engagement",   "topic",           "Engagement raised a Topic"),
    "peer_benchmark_for":                  EdgeSpec("peer_company", "chapter",         "PeerCompany serves as benchmark for Chapter"),
}
assert len(EDGE_REGISTRY) == 19, "EDGE_REGISTRY drifted from spec §2.4 (19 edges)"


class InvariantError(Exception):
    """Raised when a write would break a domain invariant (edges or §2.5 I1–I5)."""


def validate_edge(src_type: EntityType, edge_type: str, dst_type: EntityType) -> None:
    """Reject unknown edge_type or src/dst type mismatch.

    Called by BrainEngine.link() before INSERT into the links table.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.4")


def list_edge_types() -> list[str]:
    """Return all registered edge_type strings."""
    raise NotImplementedError("Step 1 R2 — just return list(EDGE_REGISTRY.keys())")
