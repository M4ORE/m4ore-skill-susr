"""susr.brain.invariants — 5 connectivity invariants (fail-closed).

These are the "anti-greenwashing" checks that gate snapshot writes and
phase commits.  Implementation strategy is split between SQL views
(declared in ddl/v001_init.sql §9–§11) and these app-level functions.

Mapping (spec §2.5):
    I1  core topic must reach an action via IRO chain
            → v_core_topic_action_coverage  + assert_i1_core_topic_coverage
    I2  chapter must conform to >=1 framework AND disclose >=1 topic
            → v_chapter_completeness        + assert_i2_chapter_completeness
    I3  every target must declare baseline+target year/value+verification
            → v_target_completeness         + assert_i3_target_completeness
    I4  every quantitative datapoint must derive_from >=1 source_doc
            → app-only (join links + entity_attributes)
    I5  every emission datapoint must calculated_with a factor whose
        effective_from <= year <= effective_to
            → app-only (date comparison)

Trigger time:
    BrainEngine.commit_phase()  — mandatory before snapshot
    health_check() MCP tool     — on-demand
    Manual via debug REPL       — `susr-mcp doctor` future

R1: signatures.  R2: implement against the helper views.
"""

from __future__ import annotations

import sqlite3

from susr.brain.edges import InvariantError


def assert_i1_core_topic_coverage(conn: sqlite3.Connection) -> None:
    """I1: every materiality_tier='核心' topic must reach an Action via
    topic_has_iro → iro_addressed_by.

    Reads v_core_topic_action_coverage; raises InvariantError listing
    up to 5 offending topic_slugs if any have action_count=0.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.5 I1")


def assert_i2_chapter_completeness(conn: sqlite3.Connection) -> None:
    """I2: every chapter must have >=1 chapter_conforms_to AND >=1 discloses_topic.

    Reads v_chapter_completeness; raises InvariantError listing offenders.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.5 I2")


def assert_i3_target_completeness(conn: sqlite3.Connection) -> None:
    """I3: every target frontmatter must have baseline_year, baseline_value,
    target_year, verification_path.

    Reads v_target_completeness; raises InvariantError if any flag is 0.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.5 I3")


def assert_i4_datapoint_source(conn: sqlite3.Connection) -> None:
    """I4: every quantitative datapoint must have >=1 datapoint_derived_from
    link to a source_doc (traceability).
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.5 I4")


def assert_i5_emission_factor_validity(conn: sqlite3.Connection) -> None:
    """I5: every emission-category datapoint must be linked via
    datapoint_calculated_with to a factor whose
    effective_from <= datapoint.year <= effective_to.
    """
    raise NotImplementedError("Step 1 R2 — see docs/research/step1-spec.md §2.5 I5")


def assert_all(conn: sqlite3.Connection) -> None:
    """Run I1..I5 in order; aggregate violations.

    Raises a single InvariantError with the concatenated messages so the
    consultant sees every problem, not just the first one.
    """
    raise NotImplementedError("Step 1 R2 — collect errors then re-raise")
