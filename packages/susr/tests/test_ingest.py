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


def test_ingest_directory_strict_mode_raises(tmp_db, tmp_path: Path) -> None:
    """``strict=True`` 時遇到 schema-fail 檔就 raise（讓 caller 知道）。

    用 tmp_path 寫一份 synthetic broken target（baseline_value 必填但缺漏）
    驗證 strict 行為。原本依賴 lealea fixture null placeholder，R6-A 已修
    fixture 改 0.0，所以改用 synthetic。
    """
    broken_dir = tmp_path / "entities" / "targets"
    broken_dir.mkdir(parents=True)
    (broken_dir / "broken.md").write_text(
        "---\n"
        "slug: broken-target\n"
        "entity_type: target\n"
        "kpi_slug: ghg-scope1\n"
        "# baseline_value 缺漏 — Pydantic 必填\n"
        "baseline_year: 2024\n"
        "target_value: 50\n"
        "target_year: 2030\n"
        "verification_path: third-party\n"
        "---\n\n# Broken\n",
        encoding="utf-8",
    )
    with pytest.raises(Exception):  # noqa: B017 — Pydantic ValidationError
        ingest_directory(tmp_db, broken_dir, strict=True)


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


# ---------------------------------------------------------------------------
# R6-B: target schema alias normalization
# ---------------------------------------------------------------------------


def test_normalize_target_value_pct_reduction_alias() -> None:
    """target_value_pct_reduction → target_value (lealea fixture 真實命中)."""
    fm = {
        "slug": "scope12-reduction-2030",
        "kpi_slug": "ghg-scope1",
        "baseline_year": 2024,
        "baseline_value": 100.0,
        "target_value_pct_reduction": 30,
        "target_year": 2030,
        "verification_path": "third-party assurance",
    }
    out = normalize_frontmatter(fm, "target")
    assert "target_value_pct_reduction" not in out
    assert out["target_value"] == 30


def test_normalize_target_year_by_alias() -> None:
    """by_year → target_year."""
    fm = {"slug": "t", "kpi_slug": "k", "by_year": 2030,
          "baseline_year": 2024, "baseline_value": 0,
          "target_value": 50, "verification_path": "x"}
    out = normalize_frontmatter(fm, "target")
    assert "by_year" not in out
    assert out["target_year"] == 2030


def test_normalize_target_alias_no_overwrite_canonical() -> None:
    """alias + canonical 同時存在 → preserve canonical，drop alias."""
    fm = {
        "slug": "t", "kpi_slug": "k",
        "baseline_year": 2024, "baseline_value": 0,
        "target_value": 99,                  # canonical
        "target_value_pct_reduction": 30,     # alias — 衝突
        "target_year": 2030, "verification_path": "x",
    }
    out = normalize_frontmatter(fm, "target")
    assert "target_value_pct_reduction" not in out
    assert out["target_value"] == 99  # canonical 保留


def test_normalize_target_idempotent() -> None:
    """normalize(normalize(x)) == normalize(x)."""
    fm = {"slug": "t", "kpi_slug": "k",
          "baseline_year": 2024, "baseline_value": 0,
          "target_value_pct_reduction": 30,
          "target_year": 2030, "verification_path": "x"}
    once = normalize_frontmatter(fm, "target")
    twice = normalize_frontmatter(once, "target")
    assert once == twice


def test_ingest_lealea_targets_now_succeeds(tmp_db) -> None:
    """ingest_directory 對 lealea entities/targets/ — 之前 0 → 現在 3."""
    repo_root = Path(__file__).resolve().parents[3]
    targets_dir = repo_root / "examples" / "lealea-5364" / "entities" / "targets"
    assert targets_dir.exists(), f"lealea targets dir missing: {targets_dir}"

    results = ingest_directory(tmp_db, targets_dir, strict=False)
    assert len(results) >= 3, (
        f"expected ≥3 lealea targets ingested, got {len(results)}: "
        f"{list(results.keys())}"
    )


# ---------------------------------------------------------------------------
# R8-3: Chapter.framework_refs → chapter_conforms_to forward rule
# ---------------------------------------------------------------------------


def test_chapter_framework_refs_auto_creates_chapter_conforms_to_edge(
    tmp_db, tmp_path: Path,
) -> None:
    """ingest chapter (含 framework_refs) + 對應 framework entity →
    自動建出 chapter_conforms_to edge（forward direction: chapter → framework）。

    這是 R8-3 加的 forward rule，用於修 R6 walkthrough §7 R8-3 揭露 — Chapter
    frontmatter 寫的 framework_refs slug list 沒自動建 chapter_conforms_to edge，
    導致 I2 invariant violation。
    """
    # 1. 建一個 framework entity
    fw_dir = tmp_path / "entities" / "frameworks"
    fw_dir.mkdir(parents=True)
    (fw_dir / "gri-305.md").write_text(
        "---\n"
        "slug: gri-305\n"
        "entity_type: framework\n"
        'version: "2016"\n'
        "disclosures:\n"
        "  - 305-1\n"
        "  - 305-2\n"
        "is_mandatory_in:\n"
        "  - TW\n"
        "---\n\n# GRI 305\n",
        encoding="utf-8",
    )

    # 2. 建一個 chapter，framework_refs 指向上面 framework
    ch_dir = tmp_path / "projects" / "p1" / "chapters"
    ch_dir.mkdir(parents=True)
    (ch_dir / "tcfd-test.md").write_text(
        "---\n"
        "slug: tcfd-test\n"
        "entity_type: chapter\n"
        "report_slug: r1\n"
        "title: TCFD Test Chapter\n"
        "framework_refs:\n"
        "  - gri-305\n"
        "owner: ESG Office\n"
        "---\n\n# TCFD Test\n",
        encoding="utf-8",
    )

    # 3. ingest 整個 tmp_path → framework 先 ingest，chapter 後 ingest（兩階段 pass）
    ingest_directory(tmp_db, tmp_path, strict=False)

    # 4. 驗證 chapter_conforms_to edge 存在（chapter 為 src，framework 為 dst）
    rows = tmp_db.execute(
        "SELECT p1.slug, p2.slug FROM links l "
        "JOIN pages p1 ON l.src_page_id = p1.id "
        "JOIN pages p2 ON l.dst_page_id = p2.id "
        "WHERE l.edge_type = 'chapter_conforms_to' "
        "AND p1.entity_type = 'chapter' "
        "AND p2.entity_type = 'framework'"
    ).fetchall()
    # R4c：brain pages.slug 已統一為 prefixed form (<plural>/<id>)
    assert ("chapters/tcfd-test", "frameworks/gri-305") in [tuple(r) for r in rows], (
        f"expected chapter_conforms_to edge chapters/tcfd-test→frameworks/gri-305, got: {rows}"
    )


def test_auto_edge_raises_on_direction_mismatch(
    tmp_db, tmp_path: Path, monkeypatch,
) -> None:
    """R9 防呆：_AUTO_EDGE_RULES 方向顛倒 → 應 raise InvariantError。

    驗收 R8-3 commit 揭露的 latent bug 類型 — 原本 chapter.discloses_topics
    放 reverse rule 但實際 EdgeSpec 是 chapter→topic（forward），方向顛倒
    繞過 validate_edge 後 silently 寫進 links 但 invariant view 抓不到。
    R9 加 validate_edge 防呆後此類 hardcoded rule bug 應 fail-loud。

    做法：monkey patch ``_AUTO_EDGE_FORWARD_RULES`` 加一條故意方向錯誤的
    rule（``iro`` 為 src，``topic_has_iro`` edge 卻定義 ``topic`` → ``iro``），
    跑 ingest_markdown_file 應 raise InvariantError。
    """
    from susr.brain import ingest as ingest_mod
    from susr.brain.edges import InvariantError

    # 先 ingest 一個 topic 讓 iro 能 resolve dst
    topic_md = tmp_path / "E1-test.md"
    topic_md.write_text(
        "---\n"
        "slug: e1-test\n"
        "entity_type: topic\n"
        "name: Test Climate\n"
        "axis: E\n"
        "impact_score: 4.0\n"
        "financial_score: 4.0\n"
        "materiality_tier: 核心\n"
        "---\n# Topic\n",
        encoding="utf-8",
    )
    ingest_markdown_file(tmp_db, topic_md)

    # 故意倒寫：把 (iro, topic_slug) 放 forward rules — IRO 為 src、topic 為 dst
    # 但 EdgeSpec topic_has_iro 是 topic→iro，所以這方向是錯的，validate_edge 應 raise
    bad_forward = dict(ingest_mod._AUTO_EDGE_FORWARD_RULES)
    bad_forward[("iro", "topic_slug")] = ("topic_has_iro", "topic", False)
    monkeypatch.setattr(ingest_mod, "_AUTO_EDGE_FORWARD_RULES", bad_forward)
    # 同時把原本正確的 reverse rule 拿掉，避免它正常建出 edge
    bad_reverse = dict(ingest_mod._AUTO_EDGE_RULES)
    bad_reverse.pop(("iro", "topic_slug"), None)
    monkeypatch.setattr(ingest_mod, "_AUTO_EDGE_RULES", bad_reverse)

    iro_md = tmp_path / "iro-test.md"
    iro_md.write_text(
        "---\n"
        "slug: iro-test\n"
        "entity_type: iro\n"
        "topic_slug: e1-test\n"
        "type: Impact\n"
        "category: physical\n"
        "time_horizon: S\n"
        "financial_magnitude: 1000000\n"
        "---\n# IRO\n",
        encoding="utf-8",
    )
    with pytest.raises(InvariantError, match="topic_has_iro"):
        ingest_markdown_file(tmp_db, iro_md)


def test_auto_edge_succeeds_on_correct_direction(tmp_db, tmp_path: Path) -> None:
    """R9：既有正確方向 rule（IRO.topic_slug → topic_has_iro reverse）→ 邊建立成功。

    這是「正常路徑」regression — 確保 validate_edge 防呆不誤殺現有 rules。
    """
    topic_md = tmp_path / "E2-test.md"
    topic_md.write_text(
        "---\n"
        "slug: e2-water\n"
        "entity_type: topic\n"
        "name: Test Water\n"
        "axis: E\n"
        "impact_score: 3.5\n"
        "financial_score: 3.5\n"
        "materiality_tier: 重大\n"
        "---\n# Topic\n",
        encoding="utf-8",
    )
    ingest_markdown_file(tmp_db, topic_md)

    iro_md = tmp_path / "iro-water.md"
    iro_md.write_text(
        "---\n"
        "slug: iro-water-shortage\n"
        "entity_type: iro\n"
        "topic_slug: e2-water\n"
        "type: Risk\n"
        "category: transition\n"
        "time_horizon: M\n"
        "financial_magnitude: 2000000\n"
        "---\n# IRO\n",
        encoding="utf-8",
    )
    ingest_markdown_file(tmp_db, iro_md)

    # 應該建出 topic_has_iro edge（topic e2-water → iro iro-water-shortage）
    rows = tmp_db.execute(
        "SELECT p1.slug, p2.slug FROM links l "
        "JOIN pages p1 ON l.src_page_id = p1.id "
        "JOIN pages p2 ON l.dst_page_id = p2.id "
        "WHERE l.edge_type = 'topic_has_iro'"
    ).fetchall()
    # R4c：brain pages.slug 已統一為 prefixed form (<plural>/<id>)
    assert ("topics/e2-water", "iros/iro-water-shortage") in [tuple(r) for r in rows], (
        f"expected topic_has_iro topics/e2-water→iros/iro-water-shortage, got: {rows}"
    )


def test_auto_edge_skips_silently_when_target_missing(
    tmp_db, tmp_path: Path,
) -> None:
    """R9：target page 不存在 → silent skip（lenient 模式不 raise）。

    這跟 direction 錯誤的行為不同 — 前者是「資料 incomplete，未來補上時
    re-ingest 即可」，後者是「hardcoded bug 該爆」。
    """
    from susr.brain.edges import InvariantError

    # Ingest IRO 但 topic 尚未 ingest（pass 1 only context）
    iro_md = tmp_path / "iro-orphan.md"
    iro_md.write_text(
        "---\n"
        "slug: iro-orphan\n"
        "entity_type: iro\n"
        "topic_slug: e9-not-yet-ingested\n"
        "type: Opportunity\n"
        "category: market\n"
        "time_horizon: L\n"
        "financial_magnitude: 500000\n"
        "---\n# Orphan IRO\n",
        encoding="utf-8",
    )
    # 不應 raise — target page 不存在是 lenient skip 範疇
    try:
        page_id = ingest_markdown_file(tmp_db, iro_md)
    except InvariantError:
        pytest.fail("target missing should silent skip, not raise InvariantError")
    assert page_id > 0  # IRO 本體 ingest 成功
    # 確認沒有任何 topic_has_iro edge 被建（target 不存在）
    edge_count = tmp_db.execute(
        "SELECT COUNT(*) FROM links WHERE edge_type = 'topic_has_iro'"
    ).fetchone()[0]
    assert edge_count == 0


def test_lealea_i2_invariant_pass_after_frameworks(tmp_db) -> None:
    """端到端：ingest 全 lealea entities/ + chapters/ 後 I2 = 0 violations。

    這是 R8-3 的 regression test — 確保未來修改不會讓 I2 再回到 5 violations。
    需要：
      - 14 個 framework entity 存在於 entities/frameworks/
      - 5 個 chapter 的 framework_refs 是 slug list（lower-case + hyphen）
      - ingest.py forward rule ("chapter", "framework_refs") wired
      - ingest.py forward rule ("chapter", "discloses_topics") wired
    """
    from susr.brain.invariants import check_all_invariants

    repo_root = Path(__file__).resolve().parents[3]
    lealea = repo_root / "examples" / "lealea-5364"
    ingest_directory(tmp_db, lealea / "entities", strict=False)
    ingest_directory(
        tmp_db,
        lealea / "projects" / "2025-sustainability-report" / "chapters",
        strict=False,
    )

    viols = check_all_invariants(tmp_db)
    i2_viols = [v for v in viols if getattr(v, "invariant_name", "") == "I2"]
    assert i2_viols == [], (
        f"expected I2 to pass after R8-3 framework wiring, got "
        f"{len(i2_viols)} violations: "
        f"{[getattr(v, 'detail', str(v)) for v in i2_viols]}"
    )

    # 同時驗證 chapter_conforms_to edge 真的有建出來（≥1 per chapter）
    chapter_count = tmp_db.execute(
        "SELECT COUNT(*) FROM pages WHERE entity_type = 'chapter' "
        "AND deleted_at IS NULL"
    ).fetchone()[0]
    edge_count = tmp_db.execute(
        "SELECT COUNT(*) FROM links WHERE edge_type = 'chapter_conforms_to'"
    ).fetchone()[0]
    assert chapter_count == 5, f"expected 5 chapters, got {chapter_count}"
    assert edge_count >= 5, (
        f"expected ≥5 chapter_conforms_to edges (1 per chapter), got {edge_count}"
    )


# ---------------------------------------------------------------------------
# Schema-level coerce: version field accepts YAML float/int (R3-A 精神延伸)
# 顧問手寫 _project.md / regulation / emission_factor 常打 `version: 0.1`
# 而非 `version: "0.1"`. Schema 嚴格 str 會在 render path 丟 fallback;
# entities.VersionStr (BeforeValidator) 在 schema 層 coerce 解決根因.
# ---------------------------------------------------------------------------


def test_report_frontmatter_accepts_float_version() -> None:
    from susr.brain.entities import ReportFrontmatter

    fm = ReportFrontmatter(
        slug="2025-sr", client_slug="acme", year=2025,
        version=0.1, language="zh-TW",
        framework_bundle=["GRI 2021"], status="draft",
    )
    assert fm.version == "0.1"
    assert isinstance(fm.version, str)


def test_report_frontmatter_accepts_int_version() -> None:
    from susr.brain.entities import ReportFrontmatter

    fm = ReportFrontmatter(
        slug="2025-sr", client_slug="acme", year=2025,
        version=1, language="zh-TW",
        framework_bundle=["GRI 2021"], status="draft",
    )
    assert fm.version == "1"


def test_report_frontmatter_quoted_string_version_unchanged() -> None:
    """Coerce 只動 int/float, 既有 str caller 不受影響."""
    from susr.brain.entities import ReportFrontmatter

    fm = ReportFrontmatter(
        slug="2025-sr", client_slug="acme", year=2025,
        version="0.1.0-beta", language="zh-TW",
        framework_bundle=["GRI 2021"], status="draft",
    )
    assert fm.version == "0.1.0-beta"


def test_report_frontmatter_rejects_invalid_version_types() -> None:
    """Coerce 只接 int/float; dict/list 仍須 raise."""
    from pydantic import ValidationError as _VE
    from susr.brain.entities import ReportFrontmatter

    for bad in ({"v": 0.1}, [0, 1], True):  # bool 不應被誤吸（is bool 排除）
        with pytest.raises(_VE):
            ReportFrontmatter(
                slug="2025-sr", client_slug="acme", year=2025,
                version=bad, language="zh-TW",
                framework_bundle=["GRI 2021"], status="draft",
            )


def test_regulation_and_emission_factor_also_accept_float_version() -> None:
    from susr.brain.entities import (
        EmissionFactorFrontmatter,
        FrameworkFrontmatter,
        RegulationFrontmatter,
    )

    reg = RegulationFrontmatter(
        slug="r1", jurisdiction="TW", authority="FSC",
        version=2.0, effective_from="2026-01-01",
        applies_to_industries=["all"],
    )
    assert reg.version == "2.0"

    ef = EmissionFactorFrontmatter(
        slug="ef1", category="electricity", region="TW", source="EPA",
        version=2024, value=0.495, unit="kgCO2e/kWh",
        effective_from="2024-01-01",
    )
    assert ef.version == "2024"

    fw = FrameworkFrontmatter(
        slug="gri", version=2021,
        disclosures=["GRI 2-1"], is_mandatory_in=["TW"],
    )
    assert fw.version == "2021"


def test_lealea_project_md_loads_with_float_version(lealea_root: Path) -> None:
    """End-to-end: lealea-5364/projects/2025-sr/_project.md (version: 0.1)
    可被 ReportFrontmatter 直接 validate, 不再走 render_docx_simple fallback layer 3."""
    import yaml
    from susr.brain.entities import ReportFrontmatter

    project_md = lealea_root / "projects" / "2025-sustainability-report" / "_project.md"
    text = project_md.read_text(encoding="utf-8")
    # Strip YAML frontmatter block (between --- markers)
    parts = text.split("---", 2)
    assert len(parts) >= 3, "_project.md 缺 YAML frontmatter"
    fm_dict = yaml.safe_load(parts[1])
    # Keep only fields known to ReportFrontmatter — _project.md may carry
    # extras (period_start / mops_filing_no) that the schema doesn't model
    known = {"slug", "entity_type", "client_slug", "year", "version",
             "language", "framework_bundle", "status", "xbrl_concept"}
    fm_dict = {k: v for k, v in fm_dict.items() if k in known}
    fm_dict.pop("entity_type", None)  # schema 不收 entity_type
    fm = ReportFrontmatter(**fm_dict)
    assert isinstance(fm.version, str)
    assert fm.version == "0.1"
