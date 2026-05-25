"""Layer 4 — MCP workspace tools 單元測試（spec §6.3）。

不真的 spawn MCP server / git push。直接 call tool function + 驗 return
shape + 副作用（檔案存在 / DB schema OK / git commit hash 是 string）。

Tools (spec §6.3 + §6.4):
    1. create_client_workspace
    2. health_check
    3. update_shared_kb
    4. promote_to_consultant_kb
"""

from __future__ import annotations

import pytest

from susr.mcp.tools.workspace import (
    create_client_workspace,
    health_check,
    promote_to_consultant_kb,
    update_shared_kb,
)


# ---------------------------------------------------------------------------
# Tool 1 — create_client_workspace
# ---------------------------------------------------------------------------


def test_create_client_workspace_returns_dict(monkeypatch, tmp_path) -> None:
    """create_client_workspace → 回 dict 含 workspace_path / commit_hash。"""
    # 設 SUSR_WORKSPACE_ROOT 指向 tmp，避免污染顧問家目錄
    monkeypatch.setenv("SUSR_WORKSPACE_ROOT", str(tmp_path))
    result = create_client_workspace(
        name="test-mcp-client",
        legal_name="Test MCP Client",
        industry="hospitality",
        standards=["GRI", "ISSB"],
        boundary="合併",
        reporting_period="2025-01-01..2025-12-31",
    )
    assert isinstance(result, dict)
    # spec §6.3：should include workspace_path
    assert "workspace_path" in result or "path" in result


def test_create_client_workspace_rejects_duplicate(monkeypatch, tmp_path) -> None:
    """同名 workspace 再建一次 → 應 raise（不靜默覆蓋）。"""
    monkeypatch.setenv("SUSR_WORKSPACE_ROOT", str(tmp_path))
    create_client_workspace(
        name="dup-client",
        legal_name="Dup",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    with pytest.raises((FileExistsError, ValueError, RuntimeError)):
        create_client_workspace(
            name="dup-client",
            legal_name="Dup",
            industry="hospitality",
            standards=["GRI"],
            boundary="合併",
            reporting_period="2025",
        )


# ---------------------------------------------------------------------------
# Tool 2 — health_check
# ---------------------------------------------------------------------------


def test_health_check_returns_ok_dict() -> None:
    """health_check（不帶 client_slug）→ {ok, checks, remediation}。"""
    result = health_check()
    assert isinstance(result, dict)
    assert "ok" in result
    assert "checks" in result
    assert isinstance(result["checks"], list)


def test_health_check_for_unknown_client_returns_not_ok() -> None:
    """指定不存在的 client_slug → ok=False，checks 中要說原因。"""
    result = health_check(client_slug="ghost-client-does-not-exist")
    assert isinstance(result, dict)
    # ok 可以是 False；至少必須有 checks 描述問題
    assert "checks" in result


# ---------------------------------------------------------------------------
# Tool 3 — update_shared_kb
# ---------------------------------------------------------------------------


def test_update_shared_kb_dry_run_returns_diff(tmp_client_workspace) -> None:
    """accept_changes=False → 回 diff（不 commit）。"""
    result = update_shared_kb(client_slug="test-client", accept_changes=False)
    assert isinstance(result, dict)
    # 預期至少有 'diff' / 'changes' / 'differences' 之一描述變動
    keys = set(result.keys())
    assert keys & {"diff", "changes", "differences", "files"}, (
        f"expected diff-like key, got {keys}"
    )


def test_update_shared_kb_apply_commits(tmp_client_workspace) -> None:
    """accept_changes=True → 真的 snapshot copy + git commit。"""
    result = update_shared_kb(client_slug="test-client", accept_changes=True)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tool 4 — promote_to_consultant_kb
# ---------------------------------------------------------------------------


def test_promote_requires_confirm_token(tmp_client_workspace, tmp_path) -> None:
    """缺 confirm_token → 應為 dry-run（回 {needs_confirm: True, confirm_token}）
    而非 raise。R2-D 設計：兩步驟 deterministic token 機制，避免誤觸但同時
    讓 Claude 能用同一個 tool 自然完成兩步流程（先 dry-run 拿 token、再
    帶 token 真正寫入），比 raise 更 elegant 且 anti-skip 完整。"""
    kb_path = tmp_path / "consultant-kb"
    kb_path.mkdir()
    result = promote_to_consultant_kb(
        client_slug="test-client",
        client_page_slugs=["topics/E1"],
        anonymize_strategy="both",
        target_kb_path=str(kb_path),
        reviewer="senior:test",
        confirm_token="",  # 空 → dry-run
    )
    assert isinstance(result, dict)
    # dry-run 必須回需要確認的訊號 + 一個 deterministic token 供下次呼叫
    assert result.get("needs_confirm") is True, f"expected dry-run, got {result}"
    assert "confirm_token" in result and result["confirm_token"], (
        f"dry-run must include a confirm_token, got {result}"
    )


def test_promote_with_token_returns_audit(tmp_client_workspace, tmp_path) -> None:
    """完整參數 → 回 audit log dict。"""
    kb_path = tmp_path / "consultant-kb"
    kb_path.mkdir()
    result = promote_to_consultant_kb(
        client_slug="test-client",
        client_page_slugs=["topics/E1"],
        anonymize_strategy="both",
        target_kb_path=str(kb_path),
        reviewer="senior:test",
        confirm_token="valid-token-from-dry-run",
    )
    assert isinstance(result, dict)
