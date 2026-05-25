"""Layer 4 — workspace.create_client_workspace skeleton 結構測試（spec §1.1）。

對 packages/susr/susr/workspace.py 的 create_client_workspace 直接驗。
重點：建出來的 layout 與 spec §1.1 per-client repo 樹一致。

預期 layout：
    <root>/<name>/
        .git/
        .susr/db.sqlite
        _client.md
        entities/{topics,stakeholders,governance,kpis,targets}/.gitkeep
        projects/
        sourcedocs/
        shared/        ← snapshot copy from susr.shared_kb.data
        .gitignore
"""

from __future__ import annotations

from pathlib import Path

import pytest

from susr.workspace import create_client_workspace, open_client_workspace, run_doctor


def test_create_client_workspace_creates_root_dir(tmp_path: Path) -> None:
    """workspace root <tmp>/<name>/ 應被建立。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME Hotels Co.",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    assert (tmp_path / "acme").is_dir()


def test_create_client_workspace_initialises_git(tmp_path: Path) -> None:
    """workspace 應 git init（.git/ 存在）。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    assert (tmp_path / "acme" / ".git").is_dir()


def test_create_client_workspace_writes_client_md(tmp_path: Path) -> None:
    """_client.md 應被建立，且包含 frontmatter。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME Hotels Co.",
        industry="hospitality",
        standards=["GRI", "ISSB"],
        boundary="合併",
        reporting_period="2025-01-01..2025-12-31",
        embedding_policy="twostage",
    )
    client_md = tmp_path / "acme" / "_client.md"
    assert client_md.is_file()
    text = client_md.read_text(encoding="utf-8")
    assert "---" in text  # frontmatter marker
    # 關鍵欄位應出現
    assert "ACME" in text or "acme" in text
    assert "hospitality" in text


def test_create_client_workspace_scaffolds_entities(tmp_path: Path) -> None:
    """entities/{topics,stakeholders,governance,kpis,targets}/ 五個子目錄。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    base = tmp_path / "acme" / "entities"
    for sub in ("topics", "stakeholders", "governance", "kpis", "targets"):
        assert (base / sub).is_dir(), f"missing entities/{sub}/"


def test_create_client_workspace_creates_projects_and_sourcedocs(tmp_path: Path) -> None:
    """projects/ 與 sourcedocs/ 兩個 top-level dir。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    assert (tmp_path / "acme" / "projects").is_dir()
    assert (tmp_path / "acme" / "sourcedocs").is_dir()


def test_create_client_workspace_creates_brain_db(tmp_path: Path) -> None:
    """.susr/db.sqlite 應被建立 + schema_version=1。"""
    import sqlite3

    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    db_path = tmp_path / "acme" / ".susr" / "db.sqlite"
    assert db_path.is_file(), ".susr/db.sqlite missing"
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row[0] == 1
    finally:
        conn.close()


def test_create_client_workspace_snapshot_shared_kb(tmp_path: Path) -> None:
    """shared/ 應 snapshot copy from package shared_kb（spec §1.1 + 決策 3）。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    shared = tmp_path / "acme" / "shared"
    assert shared.is_dir(), "shared/ snapshot dir missing"


def test_create_client_workspace_gitignore_excludes_db(tmp_path: Path) -> None:
    """.gitignore 應排除 .susr/（DB 是 derived 不入 git）。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    gi = tmp_path / "acme" / ".gitignore"
    assert gi.is_file()
    content = gi.read_text(encoding="utf-8")
    assert ".susr" in content


def test_create_client_workspace_returns_dict(tmp_path: Path) -> None:
    """回傳值應為 dict 含 path / schema_version / 等資訊。"""
    result = create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    assert isinstance(result, dict)


def test_create_client_workspace_fails_on_existing_nonempty(tmp_path: Path) -> None:
    """目標目錄已存在且非空 → 應 raise（不靜默覆蓋）。"""
    (tmp_path / "acme").mkdir()
    (tmp_path / "acme" / "stuff.md").write_text("existing", encoding="utf-8")
    with pytest.raises((FileExistsError, ValueError, RuntimeError)):
        create_client_workspace(
            root=tmp_path,
            name="acme",
            legal_name="ACME",
            industry="hospitality",
            standards=["GRI"],
            boundary="合併",
            reporting_period="2025",
        )


def test_open_client_workspace_validates_existing(tmp_path: Path) -> None:
    """open_client_workspace 對既有 workspace → 回 dict 含 schema_version。"""
    create_client_workspace(
        root=tmp_path,
        name="acme",
        legal_name="ACME",
        industry="hospitality",
        standards=["GRI"],
        boundary="合併",
        reporting_period="2025",
    )
    info = open_client_workspace(tmp_path, "acme")
    assert isinstance(info, dict)
    assert info.get("schema_version") == 1


def test_open_client_workspace_missing_raises(tmp_path: Path) -> None:
    """不存在的 client → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        open_client_workspace(tmp_path, "ghost")


def test_run_doctor_returns_bool() -> None:
    """run_doctor 應回 bool（True = 全綠）。"""
    result = run_doctor()
    assert isinstance(result, bool)
