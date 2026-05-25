# susr 顧問使用指南

## 30 秒先看這段

你接到一份新永續報告書案子，從拿到資料到交初稿，過去要 40 到 80 小時。susr 把這段壓到 8 到 15 小時，但**最終專業判斷與責任仍 100% 在你手上**。

它不會替你決定哪個議題重大，但會把 28 個候選議題列齊；不會替你寫雙重重大性結論，但會把每一個分數的來源、時間、評分者全部記下來，等客戶或確信單位回頭問「為什麼」的時候，你能在 30 秒內回得出。

它住在你自己的電腦裡。客戶資料不出機。

---

## 為什麼這份指南為你而寫

我們知道顧問每天在跟什麼搏鬥：

- **資料散在 20 個 Excel + 5 個 PDF + 3 個 ERP 截圖**：susr 的 brain 把它們吃進來，幫你檢索。
- **客戶今年的議題池跟去年不一樣，但你不確定哪裡變了**：susr 從上年 fork，差異 highlight 出來。
- **客戶問「為什麼用這個排放因子」**：susr 的 timeline + page_versions 直接拉證據鏈給你。
- **要證明這份報告通過雙重重大性**：susr 的雙軸評分輔助 + I1 invariant（核心議題必須有 action chain）會在你 commit 前先 fail-closed 擋下不完整的矩陣。
- **不想被 AI 取代，但也不想加班到凌晨三點**：susr 是 Co-pilot，不是 Replacement。

如果你覺得「我已經有自己的 SOP，為什麼要學新工具」——你的 SOP 不會被取代，susr 是讓你執行 SOP 的速度變快、可審計性變強。

---

## 怎麼讀這份指南

三條閱讀路徑，挑一條開始：

### 路徑 A：我想先理解 susr 背後的設計哲學
從 `philosophy/` 開始：

- [`philosophy/co-pilot-not-replacement.md`](philosophy/co-pilot-not-replacement.md) — 為什麼 susr 不取代你
- [`philosophy/double-materiality.md`](philosophy/double-materiality.md) — 雙重重大性在 susr 裡怎麼落地
- [`philosophy/auditable-trust.md`](philosophy/auditable-trust.md) — 每個數字都有來源
- [`philosophy/anti-greenwashing.md`](philosophy/anti-greenwashing.md) — 反綠色洗白的強制機制

### 路徑 B：我有具體案子要處理，想看實戰場景
從 `scenarios/` 開始：

- [`scenarios/接到新客戶第一週.md`](scenarios/接到新客戶第一週.md) — susr init + 上年資料 fork
- [`scenarios/議題池怎麼選.md`](scenarios/議題池怎麼選.md) — 從 28 議題池檢索與雙軸評分
- [`scenarios/客戶問為何用這個排放因子.md`](scenarios/客戶問為何用這個排放因子.md) — 用 timeline 應付確信質詢

### 路徑 C：我想知道某個具體功能怎麼用
從 `features/` 開始：

- [`features/topic-universe-search.md`](features/topic-universe-search.md) — 議題池檢索（Phase 3 第一步）
- 其餘 features 陸續補上，模板見 [`features/_template.md`](features/_template.md)

---

## 安裝 happy path（顧問版）

第一次安裝整個流程只需要碰 shell 一次，之後全部在 Claude Desktop 的聊天視窗操作。

**1. 安裝 Python 3.11 與 susr**

macOS：
```bash
brew install python@3.11
pip install "susr[embeddings-bge]"
```

Windows：到 python.org 下載 3.11 安裝程式，然後 `pip install "susr[embeddings-bge]"`。

**2. 跑一次健康檢查**

```bash
susr-mcp doctor
```

它會逐項告訴你：Python 版本、sqlite-vec 載得起來嗎、shared_kb 有沒有、Anthropic API key 有沒有設、預設 embedding 模型是哪個。任何一項紅燈，它都會給你修正指令。

**3. 設定 Claude Desktop 指向 susr**

把 susr-mcp 加進 Claude Desktop 的 `claude_desktop_config.json`（路徑 macOS 在 `~/Library/Application Support/Claude/`，Windows 在 `%APPDATA%\Claude\`），重啟 Claude Desktop。

完整 config 範例見 `docs/research/step1-spec.md §9`，這邊不複製避免過期。

**4. 你現在可以在 Claude Desktop 直接說話了**

```
顧問：幫我建一個叫 lealea-5364 的 client，旅館業，台灣上市櫃，
      合併報表邊界，報告期間 2025 年度。

Claude：[呼叫 create_client_workspace ...]
       已建立 workspace，下一步建議...
```

之後零 shell 指令。

---

## 哪裡找下一個資源

- **想了解 susr 的整體戰略定位**：看 repo 根目錄的 [`CLAUDE.md`](../../CLAUDE.md) §1
- **想看 MVP v0.1 涵蓋哪些功能**：看 [`docs/research/step1-spec.md`](../research/step1-spec.md) §0 與 §6
- **想看真實案例的端到端產出**：看 [`examples/lealea-5364/`](../../examples/lealea-5364/)
- **遇到問題想回報**：repo 的 Issues 區，標 `user-guide` label

---

## 一句話總結

susr 不是把你變成不必要的人，而是把你變成可以接更多案子、產出品質更高的人。
