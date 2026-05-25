"""Layer 4 — brain.ingest 容忍層測試（R3 P0a）。

對應 ``docs/walkthroughs/lealea-5364-phase3.md §0.42 + §7 #1``：解決
真實 SP1-004 markdown 100% ingest 失敗的問題。

驗證面向：

* normalize_frontmatter 正確處理已知 Literal token 與 PyYAML auto-parsed types
* normalize_frontmatter 為 idempotent 且 forward-compatible
* ingest_markdown_file 對真實 lealea-5364 markdown 不再 ValidationError
* ingest_directory 對整個 ``examples/lealea-5364/entities/`` 全 pass
* 預設 skip ``_legacy/`` / ``_project.md`` / ``_client.md``
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from susr.brain.entities import validate_frontmatter
from susr.brain.ingest import (
    ingest_directory,
    ingest_markdown_file,
    normalize_frontmatter,
)
from susr.brain.pages import get_frontmatter


# ---------------------------------------------------------------------------
# Path helpers — 指向真實 lealea-5364 example。
# ---------------------------------------------------------------------------


@pytest.fixture
def lealea_root(REPO_ROOT: Path) -> Path:
    """examples/lealea-5364/ 絕對路徑。"""
    return REPO_ROOT / "examples" / "lealea-5364"


# ---------------------------------------------------------------------------
# normalize_frontmatter — Literal token mapping
# ---------------------------------------------------------------------------


def test_normalize_boundary_english_to_chinese() -> None:
    """``boundary: operational_control`` → ``"營運控制"``（walkthrough §0.42 case 1）。"""
    out = normalize_frontmatter(
        {"boundary": "operational_control"}, "client",
    )
    assert out["boundary"] == "營運控制"

    # 另兩個英文 token 也要對得上
    assert normalize_frontmatter({"boundary": "financial_control"}, "client")[
        "boundary"
    ] == "合併"
    assert normalize_frontmatter({"boundary": "equity_share"}, "client")[
        "boundary"
    ] == "股權法"


def test_normalize_boundary_chinese_identity() -> None:
    """已是中文時 normalize 不改它（idempotency 的子情境）。"""
    out = normalize_frontmatter({"boundary": "營運控制"}, "client")
    assert out["boundary"] == "營運控制"


def test_normalize_assessed_at_date_to_str() -> None:
    """``assessed_at: date(2025,1,15)`` → ``"2025-01-15"``（walkthrough §0.42 case 2）。"""
    out = normalize_frontmatter(
        {"assessed_at": date(2025, 1, 15)}, "topic",
    )
    assert out["assessed_at"] == "2025-01-15"
    assert isinstance(out["assessed_at"], str)


def test_normalize_assessed_at_datetime_to_iso() -> None:
    """``datetime`` 也要被 coerce（PyYAML 對 ``YYYY-MM-DDTHH:MM:SS`` 會回 datetime）。"""
    dt = datetime(2025, 1, 15, 10, 30, 0)
    out = normalize_frontmatter({"assessed_at": dt}, "topic")
    assert out["assessed_at"] == dt.isoformat()


def test_normalize_axis_full_to_short() -> None:
    """``axis: environmental`` → ``"E"``。"""
    assert normalize_frontmatter({"axis": "environmental"}, "topic")["axis"] == "E"
    assert normalize_frontmatter({"axis": "social"}, "topic")["axis"] == "S"
    assert normalize_frontmatter({"axis": "governance"}, "topic")["axis"] == "G"
    # identity
    assert normalize_frontmatter({"axis": "E"}, "topic")["axis"] == "E"


def test_normalize_tier_english_to_chinese() -> None:
    """``materiality_tier: core`` → ``"核心"``。"""
    assert (
        normalize_frontmatter({"materiality_tier": "core"}, "topic")[
            "materiality_tier"
        ]
        == "核心"
    )
    assert (
        normalize_frontmatter({"materiality_tier": "material"}, "topic")[
            "materiality_tier"
        ]
        == "重大"
    )
    assert (
        normalize_frontmatter({"materiality_tier": "boundary"}, "topic")[
            "materiality_tier"
        ]
        == "邊界"
    )


def test_normalize_stakeholder_likert_to_float() -> None:
    """``influence_on_company: 高`` → ``5.0``（walkthrough script 也有手做這層）。"""
    out = normalize_frontmatter(
        {"influence_on_company": "高", "affected_by_company": "中"},
        "stakeholder",
    )
    assert out["influence_on_company"] == 5.0
    assert out["affected_by_company"] == 3.0


def test_normalize_iro_type_short_to_long() -> None:
    """``type: I`` → ``"Impact"``（IRO entity 容忍縮寫）。"""
    assert normalize_frontmatter({"type": "I"}, "iro")["type"] == "Impact"
    assert normalize_frontmatter({"type": "R"}, "iro")["type"] == "Risk"
    assert normalize_frontmatter({"type": "O"}, "iro")["type"] == "Opportunity"


# ---------------------------------------------------------------------------
# normalize_frontmatter — idempotency + forward-compat
# ---------------------------------------------------------------------------


def test_normalize_idempotent() -> None:
    """``normalize(normalize(x)) == normalize(x)``。"""
    raw = {
        "boundary": "operational_control",
        "stock_code": 5364,
    }
    once = normalize_frontmatter(raw, "client")
    twice = normalize_frontmatter(once, "client")
    assert once == twice


def test_normalize_preserves_unknown_keys() -> None:
    """forward-compat：未知 key 不能被吃掉。"""
    raw = {
        "boundary": "operational_control",
        "future_field_x": "some_value",
        "nested": {"deep": [1, 2, 3]},
    }
    out = normalize_frontmatter(raw, "client")
    assert out["future_field_x"] == "some_value"
    assert out["nested"] == {"deep": [1, 2, 3]}


def test_normalize_does_not_mutate_input() -> None:
    """純函式：不能 in-place 改 caller 的 dict（避免遠端副作用）。"""
    raw = {"boundary": "operational_control", "assessed_at": date(2025, 1, 15)}
    snapshot = dict(raw)
    _ = normalize_frontmatter(raw, "client")
    _ = normalize_frontmatter(raw, "topic")
    assert raw == snapshot


def test_normalize_unknown_literal_value_left_as_is() -> None:
    """未知 token 不應被 normalize 靜默改成隨便東西 — 留給 Pydantic 報錯。"""
    out = normalize_frontmatter(
        {"boundary": "totally_unknown_boundary_method"}, "client",
    )
    # 仍是原值，會在 put_page 內 Pydantic 報錯
    assert out["boundary"] == "totally_unknown_boundary_method"


def test_normalize_stock_code_int_to_str() -> None:
    """``stock_code: "5364"`` 無引號被 PyYAML parse 成 int → coerce 回 str。"""
    out = normalize_frontmatter({"stock_code": 5364}, "client")
    assert out["stock_code"] == "5364"


# ---------------------------------------------------------------------------
# 真實 lealea-5364 markdown ingest
# ---------------------------------------------------------------------------


def test_ingest_markdown_file_lealea_client(tmp_db, lealea_root: Path) -> None:
    """真實 ``examples/lealea-5364/_client.md`` 過得了 normalize + put_page。

    這檔的 ``boundary: operational_control`` 是 walkthrough §0.42 第一個失敗 case。
    """
    client_md = lealea_root / "_client.md"
    page_id = ingest_markdown_file(tmp_db, client_md)
    assert page_id > 0

    fm = get_frontmatter(tmp_db, page_id)
    assert fm["boundary"] == "營運控制"
    assert fm["slug"] == "lealea-5364"


def test_ingest_markdown_file_lealea_topic(tmp_db, lealea_root: Path) -> None:
    """真實 ``entities/topics/E1-climate.md`` 過得了（walkthrough §0.42 case 2）。

    ``assessed_at: 2025-01-15`` 會被 PyYAML 解成 ``date``，必須被 coerce。
    """
    topic_md = lealea_root / "entities" / "topics" / "E1-climate.md"
    page_id = ingest_markdown_file(tmp_db, topic_md)
    assert page_id > 0

    fm = get_frontmatter(tmp_db, page_id)
    assert isinstance(fm["assessed_at"], str)
    assert fm["assessed_at"] == "2025-01-15"
    assert fm["axis"] == "E"
    assert fm["materiality_tier"] == "核心"


def test_ingest_directory_lealea_entities(tmp_db, lealea_root: Path) -> None:
    """bulk ingest ``examples/lealea-5364/entities/`` 大部分檔成功。

    這是 walkthrough 揭露「真實 markdown 100% ingest 失敗」的反向驗證。
    Walkthrough §0.42 只 ingest 13 topics + 3 stakeholders 子集；我們這裡
    跑完整 entities/ 子樹（28 topics + 7 stakeholders + 8 kpis + 3 targets
    + 2 governance ≈ 48 檔），預期大多數成功 — 個別 target / governance
    可能因真實檔缺欄位 / 命名不一致（如 ``target_value_pct_reduction``
    vs schema 要 ``target_value``）而失敗，這由 ``strict=False`` 容忍。
    """
    entities_dir = lealea_root / "entities"
    results = ingest_directory(tmp_db, entities_dir)

    # 至少所有 topics + stakeholders 該過（這兩類是 walkthrough 已驗證）
    # 28 topics + 7 stakeholders = 35，再加大部分 kpi (8) 應 ≥ 40
    assert len(results) >= 40, f"expected ≥40 ingested files, got {len(results)}"

    # DB row count 與 results 對齊
    page_count = tmp_db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    assert page_count == len(results)

    # entity_type 分布該包含至少 3 種
    types = tmp_db.execute(
        "SELECT DISTINCT entity_type FROM pages"
    ).fetchall()
    type_set = {row[0] for row in types}
    assert "topic" in type_set
    assert "stakeholder" in type_set
    assert "kpi" in type_set


def test_ingest_directory_strict_mode_raises(tmp_db, lealea_root: Path) -> None:
    """``strict=True`` 時遇到 schema-fail 檔就 raise（讓 caller 知道）。"""
    # tcfd-net-zero-2050.md 有 baseline_value: null（schema 要 float）—
    # 開 strict 一定會炸；不開不會。
    targets_dir = lealea_root / "entities" / "targets"
    with pytest.raises(Exception):  # noqa: B017 — Pydantic ValidationError
        ingest_directory(tmp_db, targets_dir, strict=True)


def test_ingest_skips_legacy_dir(tmp_db, lealea_root: Path) -> None:
    """``_legacy/`` 內檔預設**不**被 ingest（schema 不對齊，會 ValidationError）。"""
    # 對整個 lealea-5364/ root 跑，但連 _client.md 也預設跳過
    results = ingest_directory(tmp_db, lealea_root)

    # 沒有任何結果的 path 應該包含 _legacy
    legacy_paths = [p for p in results if "_legacy" in p]
    assert legacy_paths == [], f"_legacy/ should be skipped, got: {legacy_paths}"

    # 開 include_legacy 時也不應該 crash（但 legacy schema 可能會 fail）—
    # 我們不在此測試 include_legacy=True，因為 _legacy 內檔本來就不是 entity schema


def test_ingest_skips_client_and_project_files(tmp_db, lealea_root: Path) -> None:
    """``_client.md`` / ``_project.md`` 預設 skip（特殊主檔由 helper 處理）。"""
    results = ingest_directory(tmp_db, lealea_root)
    main_files = [p for p in results if Path(p).name in ("_client.md", "_project.md")]
    assert main_files == [], (
        f"_client.md / _project.md should be skipped by default, "
        f"got: {main_files}"
    )


def test_ingest_handles_no_frontmatter(tmp_db, tmp_path: Path) -> None:
    """無 frontmatter 的 ``.md`` 應 raise ``ValueError``（fail-closed）。

    Design choice: 我們選 **raise 而非 silent skip**，因為「ingest 失敗」是
    R3 P0a 要解決的問題；如果出現非預期的無 frontmatter 檔，靜默 skip 會
    讓顧問誤以為「全部 ingest 成功」。Symptom out the source: 出現這檔代表
    上游有問題，should be loud。
    """
    empty_md = tmp_path / "no-fm.md"
    empty_md.write_text("# This file has no YAML frontmatter\n\nbody only.", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        ingest_markdown_file(tmp_db, empty_md)


# ---------------------------------------------------------------------------
# Bonus — 驗證 normalize 輸出能通過真正的 Pydantic schema 驗證
# （這是這層存在的全部理由）
# ---------------------------------------------------------------------------


def test_normalize_output_passes_pydantic_for_lealea_client(
    lealea_root: Path,
) -> None:
    """端到端：真實 _client.md frontmatter normalize 後過 Pydantic validation。"""
    import yaml

    raw_md = (lealea_root / "_client.md").read_text(encoding="utf-8")
    # 切 frontmatter
    end = raw_md.find("\n---", 3)
    fm = yaml.safe_load(raw_md[3:end].strip())
    fm.pop("entity_type", None)
    normalized = normalize_frontmatter(fm, "client")
    # 真正驗證 — 不該 raise
    validate_frontmatter("client", normalized)


def test_normalize_output_passes_pydantic_for_lealea_topic(
    lealea_root: Path,
) -> None:
    """端到端：真實 E1-climate.md frontmatter normalize 後過 Pydantic validation。"""
    import yaml

    raw_md = (lealea_root / "entities" / "topics" / "E1-climate.md").read_text(
        encoding="utf-8",
    )
    end = raw_md.find("\n---", 3)
    fm = yaml.safe_load(raw_md[3:end].strip())
    fm.pop("entity_type", None)
    normalized = normalize_frontmatter(fm, "topic")
    validate_frontmatter("topic", normalized)
