"""Layer 4 — MCP Phase 6 in-process docx renderer 單元測試。

對應 ``packages/susr/susr/mcp/tools/phase6_render.py``：

    1. render_docx_payload_to_path  — 純渲染函式
    2. render_docx_simple           — MCP tool 一條龍

測試覆蓋（user spec 7 條 → 此檔 8 個 test）：

    1. test_render_minimal_payload_produces_docx_above_5kb
    2. test_render_lealea_full_payload_above_30kb
    3. test_render_docx_simple_counts_match_lealea_fixture
    4. test_render_docx_simple_writes_timeline_entry
    5. test_render_docx_simple_missing_client_raises_filenotfound
    6. test_render_raises_render_error_when_docx_unavailable
    7. test_render_warnings_include_no_chapters_for_empty_payload
    8. test_render_docx_simple_registered_in_server

不靠 spawn MCP server；直接呼叫 tool function + brain engine + python-docx。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from susr.brain.engine import BrainEngine
from susr.mcp.tools.phase6 import (
    ChapterPayload,
    ClientProfilePayload,
    DocxPayload,
    IroPayload,
    KpiPayload,
    MaterialityMatrixPayload,
    TargetPayload,
    prepare_docx_payload,
)
from susr.mcp.tools.phase6_render import (
    DocxRenderResult,
    RenderError,
    render_docx_payload_to_path,
    render_docx_simple,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
LEALEA_FIXTURE = REPO_ROOT / "examples" / "lealea-5364"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ws_path(tmp_client_workspace: Any) -> Path:
    if isinstance(tmp_client_workspace, dict):
        return Path(tmp_client_workspace["workspace_path"])
    return Path(tmp_client_workspace)


def _minimal_payload() -> DocxPayload:
    """1 chapter / 0 IRO / 0 KPI / 0 target — smallest viable payload."""
    return DocxPayload(
        client=ClientProfilePayload(
            slug="mini-co", legal_name="Mini Co., Ltd.",
            industry="hospitality", stock_code=None,
        ),
        reporting_period="2025-01-01..2025-12-31",
        frameworks=["GRI Standards 2021"],
        chapters=[
            ChapterPayload(
                title="關於本報告",
                slug="ch-about",
                content_md="# 關於本報告\n\n本公司 2025 年度永續報告書。\n",
                order=1,
                framework_refs=["GRI 2-1"],
            ),
        ],
        materiality_matrix=MaterialityMatrixPayload(),
        iros=[],
        kpis_summary=[],
        targets_summary=[],
        gri_content_index_ref=None,
        annex={"project_slug": "2025-sustainability-report"},
        invocation_hint="(test)",
    )


def _ingest_lealea_into(ws_path: Path) -> int:
    """Copy lealea entities + chapters into ws + ingest into brain DB.

    Mirrors gen_lealea_docx.build_payload() but works against an existing
    tmp_client_workspace（已被 fixture 建好基本 entities 目錄）。
    """
    from susr.brain.ingest import ingest_directory

    for sub in ("entities", "projects"):
        src = LEALEA_FIXTURE / sub
        dst = ws_path / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    db_path = ws_path / ".susr" / "db.sqlite"
    engine = BrainEngine.open(str(db_path), load_sqlite_vec=False)
    try:
        ent = ingest_directory(engine.conn, ws_path / "entities", strict=False)
        ch = ingest_directory(
            engine.conn,
            ws_path / "projects" / "2025-sustainability-report" / "chapters",
            strict=False,
        )
    finally:
        engine.close()
    return len(ent) + len(ch)


# ---------------------------------------------------------------------------
# Test 1: minimal payload → docx > 5KB
# ---------------------------------------------------------------------------


def test_render_minimal_payload_produces_docx_above_5kb(tmp_path: Path) -> None:
    """render_docx_payload_to_path on minimal payload produces a real .docx."""
    out_path = tmp_path / "mini.docx"
    warnings = render_docx_payload_to_path(_minimal_payload(), out_path, year_hint=2025)
    assert out_path.exists()
    size_bytes = out_path.stat().st_size
    assert size_bytes > 5_000, f"expected > 5KB, got {size_bytes}"
    # zero IROs / KPIs / targets surface as warnings but not as failures
    assert "no_iros" in warnings
    assert "no_kpis" in warnings
    assert "no_targets" in warnings
    # has chapters → no_chapters NOT in warnings
    assert "no_chapters" not in warnings


# ---------------------------------------------------------------------------
# Test 2: full lealea payload → docx > 30KB
# ---------------------------------------------------------------------------


def test_render_lealea_full_payload_above_30kb(tmp_client_workspace, tmp_path: Path) -> None:
    """Build full lealea payload via prepare_docx_payload + render → > 30KB."""
    ws_path = _ws_path(tmp_client_workspace)
    _ingest_lealea_into(ws_path)

    payload = prepare_docx_payload(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    out_path = tmp_path / "lealea_full.docx"
    warnings = render_docx_payload_to_path(payload, out_path, year_hint=2025)
    assert out_path.exists()
    size_bytes = out_path.stat().st_size
    assert size_bytes > 30_000, f"expected > 30KB, got {size_bytes}; warnings={warnings}"


# ---------------------------------------------------------------------------
# Test 3: render_docx_simple returns expected counts vs lealea fixture
# ---------------------------------------------------------------------------


def test_render_docx_simple_counts_match_lealea_fixture(tmp_client_workspace) -> None:
    """End-to-end: render_docx_simple against ingested lealea returns the
    documented counts (5 chapters / 14 IROs / 9 KPIs / 6 targets)."""
    ws_path = _ws_path(tmp_client_workspace)
    _ingest_lealea_into(ws_path)

    result = render_docx_simple(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    assert isinstance(result, DocxRenderResult)
    assert result.chapter_count == 5, f"expected 5 chapters, got {result.chapter_count}"
    assert result.iro_count == 14, f"expected 14 IROs, got {result.iro_count}"
    assert result.kpi_count == 9, f"expected 9 KPIs, got {result.kpi_count}"
    assert result.target_count == 6, f"expected 6 targets, got {result.target_count}"
    # output_path under projects/2025-sustainability-report/output/Report_2025.docx
    expected_out = ws_path / "projects" / "2025-sustainability-report" / "output" / "Report_2025.docx"
    assert Path(result.output_path) == expected_out
    assert expected_out.exists()
    assert result.size_bytes > 30_000


# ---------------------------------------------------------------------------
# Test 4: render_docx_simple writes timeline_entry to brain DB
# ---------------------------------------------------------------------------


def test_render_docx_simple_writes_timeline_entry(tmp_client_workspace) -> None:
    """After render_docx_simple, brain timeline_entries should contain a row
    with payload['action'] == 'render_docx_simple'."""
    import json

    ws_path = _ws_path(tmp_client_workspace)
    _ingest_lealea_into(ws_path)

    result = render_docx_simple(
        client_slug="test-client", year=2025, project_slug="2025-sustainability-report",
    )
    assert result.timeline_entry_id > 0

    # Inspect brain DB directly — find a timeline_entries row matching action
    db_path = ws_path / ".susr" / "db.sqlite"
    engine = BrainEngine.open(str(db_path), load_sqlite_vec=False)
    try:
        rows = engine.conn.execute(
            "SELECT id, page_id, action_type, payload FROM timeline_entries "
            "ORDER BY id DESC LIMIT 50"
        ).fetchall()
    finally:
        engine.close()

    matching = []
    for tl_id, page_id, action_type, payload_json in rows:
        try:
            pl = json.loads(payload_json) if payload_json else {}
        except (TypeError, ValueError):
            pl = {}
        if pl.get("action") == "render_docx_simple":
            matching.append((tl_id, page_id, action_type, pl))

    assert matching, f"expected a render_docx_simple timeline row; got {len(rows)} recent entries"
    tl_id, page_id, action_type, pl = matching[0]
    assert pl["chapter_count"] == 5
    assert pl["renderer_version"] == "v0.1"
    assert pl["size_bytes"] > 30_000


# ---------------------------------------------------------------------------
# Test 5: missing client_slug → FileNotFoundError
# ---------------------------------------------------------------------------


def test_render_docx_simple_missing_client_raises_filenotfound(
    tmp_path: Path, monkeypatch,
) -> None:
    """find_client_workspace raises FileNotFoundError if no _client.md."""
    monkeypatch.setenv("SUSR_WORKSPACE_ROOT", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        render_docx_simple(client_slug="does-not-exist", year=2025)


# ---------------------------------------------------------------------------
# Test 6: python-docx unavailable → RenderError
# ---------------------------------------------------------------------------


def test_render_raises_render_error_when_docx_unavailable(
    tmp_path: Path, monkeypatch,
) -> None:
    """Simulate ``import docx`` failing → render raises RenderError."""
    # Strip cached docx imports so ``import docx`` inside _ensure_docx re-runs.
    for mod in [m for m in list(sys.modules) if m == "docx" or m.startswith("docx.")]:
        monkeypatch.delitem(sys.modules, mod, raising=False)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "docx" or name.startswith("docx."):
            raise ImportError(f"simulated: {name} not installed")
        return real_import(name, globals, locals, fromlist, level)

    if isinstance(__builtins__, dict):
        monkeypatch.setitem(__builtins__, "__import__", fake_import)
    else:
        monkeypatch.setattr(__builtins__, "__import__", fake_import)

    out_path = tmp_path / "fail.docx"
    with pytest.raises(RenderError) as exc_info:
        render_docx_payload_to_path(_minimal_payload(), out_path)
    assert "python-docx" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 7: warnings include no_chapters for empty payload
# ---------------------------------------------------------------------------


def test_render_warnings_include_no_chapters_for_empty_payload(tmp_path: Path) -> None:
    """Payload with empty chapters[] should not raise; warnings includes 'no_chapters'."""
    payload = _minimal_payload()
    payload.chapters = []  # strip chapters
    out_path = tmp_path / "no_chapters.docx"
    warnings = render_docx_payload_to_path(payload, out_path)
    assert out_path.exists()
    assert "no_chapters" in warnings
    # Still produces a docx (cover + materiality + appendices placeholder)
    assert out_path.stat().st_size > 3_000


# ---------------------------------------------------------------------------
# Test 8: server registration (skip if mcp SDK missing or registry opaque)
# ---------------------------------------------------------------------------


def test_render_docx_simple_registered_in_server() -> None:
    """``render_docx_simple`` should appear in the FastMCP server tool registry."""
    try:
        from susr.mcp.server import create_server
        server = create_server()
    except ImportError:
        pytest.skip("mcp SDK not installed in this environment")

    names: set[str] = set()
    for attr_path in (
        ("_tool_manager", "_tools"),
        ("_tools",),
    ):
        obj: Any = server
        try:
            for a in attr_path:
                obj = getattr(obj, a)
            if isinstance(obj, dict):
                names = set(obj.keys())
                break
        except AttributeError:
            continue

    if not names:
        pytest.skip("FastMCP internal registry 不可內省 — skip introspection assertion")

    assert "render_docx_simple" in names, (
        f"render_docx_simple missing from registered tools; got {sorted(names)}"
    )
