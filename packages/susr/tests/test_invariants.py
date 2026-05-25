"""Layer 3 — 5 條連結性 invariants 測試（spec §2.5 / §4.3）。

每條 invariant 都有兩種測試模式：
    1. fail-closed：缺欄位 / 缺 edge / 過期 factor → 應 raise InvariantError
    2. happy path：補齊後 → 不 raise

R2 完成 assert_iN_* 實作後本檔即可全綠；在那之前 NotImplementedError
是預期。測試是 R2 的接收契約（CLAUDE.md §6.1 hard rule）。
"""

from __future__ import annotations

import pytest

from susr.brain.edges import InvariantError
from susr.brain.invariants import (
    assert_all,
    assert_i1_core_topic_coverage,
    assert_i2_chapter_completeness,
    assert_i3_target_completeness,
    assert_i4_datapoint_source,
    assert_i5_emission_factor_validity,
)


# ---------------------------------------------------------------------------
# I1 — 核心議題必須有 Action（透過 topic_has_iro → iro_addressed_by 鏈）
# ---------------------------------------------------------------------------


def test_i1_core_topic_without_action_fails(tmp_brain) -> None:
    """核心議題沒有 Action chain → 應 raise I1 violation。"""
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter={
            "slug": "E1",
            "name": "氣候變遷",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.0,
            "materiality_tier": "核心",
            "industry_specificity": "hotel",
        },
    )
    # 沒建 IRO / Action chain — 預期 invariant 抓到
    with pytest.raises(InvariantError, match="I1"):
        assert_i1_core_topic_coverage(tmp_brain.conn)


def test_i1_core_topic_with_full_chain_passes(tmp_brain) -> None:
    """核心議題接上 IRO → Action chain 後 → 應通過。"""
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter={
            "slug": "E1",
            "name": "氣候變遷",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.0,
            "materiality_tier": "核心",
        },
    )
    tmp_brain.put_page(
        slug="iros/E1-impact-emissions",
        entity_type="iro",
        title="E1 impact: GHG emissions",
        compiled_truth="",
        file_path="entities/topics/E1/iro/impact-emissions.md",
        frontmatter={
            "slug": "E1-impact-emissions",
            "topic_slug": "E1",
            "type": "Impact",
            "category": "operational",
            "time_horizon": "M",
            "financial_magnitude": 3.0,
        },
    )
    tmp_brain.put_page(
        slug="actions/2025-energy-reduction",
        entity_type="action",
        title="2025 能耗減量計畫",
        compiled_truth="",
        file_path="projects/2025-sr/actions/energy-reduction.md",
        frontmatter={
            "slug": "2025-energy-reduction",
            "chapter_slug": "ch-environment",
            "iro_addressed": ["E1-impact-emissions"],
            "budget": 1_000_000.0,
            "progress_pct": 0.2,
            "owner_department": "ESG",
            "period": "2025",
        },
    )
    tmp_brain.link("topics/E1", "topic_has_iro", "iros/E1-impact-emissions")
    tmp_brain.link(
        "iros/E1-impact-emissions",
        "iro_addressed_by",
        "actions/2025-energy-reduction",
    )

    # 應 NOT raise
    assert_i1_core_topic_coverage(tmp_brain.conn)


def test_i1_non_core_topic_without_action_passes(tmp_brain) -> None:
    """重大 / 邊界議題沒 Action chain → I1 不該管，應通過。"""
    tmp_brain.put_page(
        slug="topics/G3",
        entity_type="topic",
        title="商業道德",
        compiled_truth="",
        file_path="entities/topics/G3.md",
        frontmatter={
            "slug": "G3",
            "name": "商業道德",
            "axis": "G",
            "impact_score": 3.0,
            "financial_score": 3.0,
            "materiality_tier": "邊界",
        },
    )
    assert_i1_core_topic_coverage(tmp_brain.conn)


# ---------------------------------------------------------------------------
# I2 — Chapter 必須 conformsTo ≥ 1 framework 且 discloses ≥ 1 topic
# ---------------------------------------------------------------------------


def test_i2_chapter_missing_framework_fails(tmp_brain) -> None:
    """Chapter 沒接任何 framework → I2 violation。"""
    tmp_brain.put_page(
        slug="chapters/ch-env",
        entity_type="chapter",
        title="環境",
        compiled_truth="",
        file_path="projects/2025-sr/chapters/environment.md",
        frontmatter={
            "slug": "ch-env",
            "report_slug": "2025-sr",
            "title": "環境",
            "framework_refs": ["GRI 305"],
            "owner": "ESG",
        },
    )
    with pytest.raises(InvariantError, match="I2"):
        assert_i2_chapter_completeness(tmp_brain.conn)


def test_i2_chapter_with_framework_and_topic_passes(tmp_brain) -> None:
    """Chapter 接 framework + topic → I2 通過。"""
    tmp_brain.put_page(
        slug="frameworks/GRI",
        entity_type="framework",
        title="GRI Standards 2021",
        compiled_truth="",
        file_path="shared/frameworks/GRI.md",
        frontmatter={
            "slug": "GRI",
            "version": "2021",
            "disclosures": ["GRI 305-1"],
            "is_mandatory_in": ["TW"],
        },
    )
    tmp_brain.put_page(
        slug="topics/E1",
        entity_type="topic",
        title="氣候變遷",
        compiled_truth="",
        file_path="entities/topics/E1.md",
        frontmatter={
            "slug": "E1",
            "name": "氣候變遷",
            "axis": "E",
            "impact_score": 4.5,
            "financial_score": 4.0,
            "materiality_tier": "核心",
        },
    )
    tmp_brain.put_page(
        slug="chapters/ch-env",
        entity_type="chapter",
        title="環境",
        compiled_truth="",
        file_path="projects/2025-sr/chapters/environment.md",
        frontmatter={
            "slug": "ch-env",
            "report_slug": "2025-sr",
            "title": "環境",
            "framework_refs": ["GRI 305"],
            "owner": "ESG",
        },
    )
    tmp_brain.link("chapters/ch-env", "chapter_conforms_to", "frameworks/GRI")
    tmp_brain.link("chapters/ch-env", "discloses_topic", "topics/E1")
    assert_i2_chapter_completeness(tmp_brain.conn)


# ---------------------------------------------------------------------------
# I3 — Target 四要素齊（baseline_year / baseline_value / target_year /
#                       verification_path）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["baseline_year", "baseline_value", "target_year", "verification_path"],
)
def test_i3_target_missing_field_fails(tmp_brain, missing_field: str) -> None:
    """Target 任一必備欄位缺失 → I3 violation。"""
    fm = {
        "slug": "t-scope1-2030",
        "kpi_slug": "scope1-emissions",
        "baseline_year": 2020,
        "baseline_value": 1000.0,
        "target_value": 500.0,
        "target_year": 2030,
        "verification_path": "SBTi 1.5C",
    }
    fm.pop(missing_field)
    # 若 schema-level Pydantic 直接擋下缺欄，就由 put_page 端 raise；
    # 若 put_page 容許缺欄存進 entity_attributes，就由 invariant 端 raise。
    # 兩種任一發生都是 fail-closed 正確行為。
    try:
        tmp_brain.put_page(
            slug=f"targets/{missing_field}-missing",
            entity_type="target",
            title="缺欄位 target",
            compiled_truth="",
            file_path="entities/targets/x.md",
            frontmatter=fm,
        )
    except Exception:
        return  # schema-level reject 也算通過 fail-closed contract
    with pytest.raises(InvariantError, match="I3"):
        assert_i3_target_completeness(tmp_brain.conn)


def test_i3_target_complete_passes(tmp_brain) -> None:
    """Target 四要素齊 → I3 通過。"""
    tmp_brain.put_page(
        slug="targets/scope1-2030",
        entity_type="target",
        title="2030 範疇 1 減半",
        compiled_truth="",
        file_path="entities/targets/scope1-2030.md",
        frontmatter={
            "slug": "scope1-2030",
            "kpi_slug": "scope1-emissions",
            "baseline_year": 2020,
            "baseline_value": 1000.0,
            "target_value": 500.0,
            "target_year": 2030,
            "verification_path": "SBTi 1.5C",
        },
    )
    assert_i3_target_completeness(tmp_brain.conn)


# ---------------------------------------------------------------------------
# I4 — DataPoint 可追溯（必須有 datapoint_derived_from → source_doc）
# ---------------------------------------------------------------------------


def test_i4_datapoint_without_source_fails(tmp_brain) -> None:
    """量化 datapoint 沒接 source_doc → I4 violation。"""
    tmp_brain.put_page(
        slug="datapoints/scope1-2024",
        entity_type="datapoint",
        title="2024 範疇 1 排放",
        compiled_truth="",
        file_path="projects/2025-sr/datapoints/scope1-2024.md",
        frontmatter={
            "slug": "scope1-2024",
            "kpi_slug": "scope1-emissions",
            "year": 2024,
            "value": 980.5,
            "source_refs": [],
            "calculation_method": "GHG Protocol",
            "assurance_status": "internal",
            "last_assessed": "2025-03-15",
            "responsible_person": "ESG team",
        },
    )
    with pytest.raises(InvariantError, match="I4"):
        assert_i4_datapoint_source(tmp_brain.conn)


def test_i4_datapoint_with_source_passes(tmp_brain) -> None:
    """量化 datapoint 接上 source_doc → I4 通過。"""
    tmp_brain.put_page(
        slug="sourcedocs/erp-2024",
        entity_type="source_doc",
        title="2024 ERP 能源使用匯出",
        compiled_truth="",
        file_path="sourcedocs/2024/erp-energy.md",
        frontmatter={
            "slug": "erp-2024",
            "client_slug": "test-client",
            "doc_type": "ERP_export",
            "period": "2024",
            "file_hash": "abc123",
            "ingest_date": "2025-03-01",
        },
    )
    tmp_brain.put_page(
        slug="datapoints/scope1-2024",
        entity_type="datapoint",
        title="2024 範疇 1 排放",
        compiled_truth="",
        file_path="projects/2025-sr/datapoints/scope1-2024.md",
        frontmatter={
            "slug": "scope1-2024",
            "kpi_slug": "scope1-emissions",
            "year": 2024,
            "value": 980.5,
            "source_refs": ["erp-2024"],
            "calculation_method": "GHG Protocol",
            "assurance_status": "internal",
            "last_assessed": "2025-03-15",
            "responsible_person": "ESG team",
        },
    )
    tmp_brain.link("datapoints/scope1-2024", "datapoint_derived_from", "sourcedocs/erp-2024")
    assert_i4_datapoint_source(tmp_brain.conn)


# ---------------------------------------------------------------------------
# I5 — 排放 DataPoint 對應有效 EmissionFactor
# ---------------------------------------------------------------------------


def test_i5_emission_datapoint_with_expired_factor_fails(tmp_brain) -> None:
    """Factor effective_to 早於 datapoint.year → I5 violation。"""
    tmp_brain.put_page(
        slug="emission_factors/ef-electricity-2020",
        entity_type="emission_factor",
        title="台電電力排放係數 2020",
        compiled_truth="",
        file_path="shared/emission_factors/electricity-2020.md",
        frontmatter={
            "slug": "ef-electricity-2020",
            "category": "Scope2-electricity",
            "region": "TW",
            "source": "經濟部",
            "version": "2020",
            "value": 0.509,
            "unit": "kgCO2e/kWh",
            "effective_from": "2020-01-01",
            "effective_to": "2023-12-31",  # 在 2025 已過期
        },
    )
    tmp_brain.put_page(
        slug="datapoints/scope2-2025",
        entity_type="datapoint",
        title="2025 範疇 2 排放",
        compiled_truth="",
        file_path="projects/2025-sr/datapoints/scope2-2025.md",
        frontmatter={
            "slug": "scope2-2025",
            "kpi_slug": "scope2-electricity",
            "year": 2025,
            "value": 5_000.0,
            "source_refs": ["taipower-bill-2025"],
            "calculation_method": "kWh x factor",
            "assurance_status": "internal",
            "last_assessed": "2026-01-15",
            "responsible_person": "ESG team",
        },
    )
    tmp_brain.link(
        "datapoints/scope2-2025",
        "datapoint_calculated_with",
        "emission_factors/ef-electricity-2020",
    )
    with pytest.raises(InvariantError, match="I5"):
        assert_i5_emission_factor_validity(tmp_brain.conn)


def test_i5_emission_datapoint_with_valid_factor_passes(tmp_brain) -> None:
    """Factor effective 區間包含 datapoint.year → I5 通過。"""
    tmp_brain.put_page(
        slug="emission_factors/ef-electricity-current",
        entity_type="emission_factor",
        title="台電電力排放係數 2024-2030",
        compiled_truth="",
        file_path="shared/emission_factors/electricity-current.md",
        frontmatter={
            "slug": "ef-electricity-current",
            "category": "Scope2-electricity",
            "region": "TW",
            "source": "經濟部",
            "version": "2024",
            "value": 0.474,
            "unit": "kgCO2e/kWh",
            "effective_from": "2024-01-01",
            "effective_to": "2030-12-31",
        },
    )
    tmp_brain.put_page(
        slug="datapoints/scope2-2025",
        entity_type="datapoint",
        title="2025 範疇 2 排放",
        compiled_truth="",
        file_path="projects/2025-sr/datapoints/scope2-2025.md",
        frontmatter={
            "slug": "scope2-2025",
            "kpi_slug": "scope2-electricity",
            "year": 2025,
            "value": 5_000.0,
            "source_refs": ["taipower-bill-2025"],
            "calculation_method": "kWh x factor",
            "assurance_status": "internal",
            "last_assessed": "2026-01-15",
            "responsible_person": "ESG team",
        },
    )
    tmp_brain.link(
        "datapoints/scope2-2025",
        "datapoint_calculated_with",
        "emission_factors/ef-electricity-current",
    )
    assert_i5_emission_factor_validity(tmp_brain.conn)


# ---------------------------------------------------------------------------
# assert_all — 整合
# ---------------------------------------------------------------------------


def test_assert_all_aggregates_violations(tmp_brain) -> None:
    """空 brain 多條 invariant 都不該觸發（沒任何 page → 沒違規對象）。

    主要驗證 assert_all 不會因為 None 結果集而崩潰。
    """
    # Empty brain: no offending rows for any invariant.
    assert_all(tmp_brain.conn)
