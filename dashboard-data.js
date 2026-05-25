// susr · Dashboard data source
// 修改此檔即可更新 dashboard.html 顯示內容。
// 與 docs/{defeinition,target,product_structure}.md 內容如有牴觸，以 docs/ 為準。
window.SUSR_DASHBOARD = {
  "meta": {
    "project": "susr",
    "canonicalName": "sustainability-report",
    "tagline": "顧問的第二大腦 · ESG Report Co-pilot",
    "updated": "2026-05-25",
    "version": "v0.1 (post-pivot)",
    "northStar": "把顧問寫永續報告的時間從 40-80h 壓縮到 8-15h，同時讓品質、框架完整度、故事性都提升 — 而且 100% 保留顧問的專業判斷與最終責任。"
  },

  "principles": [
    {
      "id": "definition",
      "file": "docs/defeinition.md",
      "title": "Definition · 永續報告書是什麼",
      "headline": "把 ESG 表現以可驗證、可比較、可信任的方式結構化呈現給利害關係人",
      "atoms": [
        { "name": "資料 (Data)", "desc": "原始、分散、非結構化的 ESG 資料：碳排、用水、廢棄物、人權、供應鏈、治理…" },
        { "name": "框架對應 (Framework Mapping)", "desc": "精準對應 GRI、SASB、TCFD、ISSB、CSRD、台灣永續報告書指引、香港 ESG 守則" },
        { "name": "敘事與判斷 (Narrative + Judgment)", "desc": "雙重重大性評估、風險揭露、目標設定 — 需要人類脈絡理解" },
        { "name": "信任與驗證 (Assurance & Trust)", "desc": "通過第三方確信、投資人審查、監管檢查" }
      ],
      "copilotVsReplacement": {
        "rows": [
          ["面向", "Co-pilot ✅", "Replacement ❌"],
          ["目標客戶", "輔導顧問 / ESG 顧問公司", "企業（尤其想省錢的中小企業）"],
          ["商業模式", "SaaS 訂閱（顧問公司月費）", "按報告計價或企業訂閱"],
          ["顧問反應", "視為幫手，願意推廣", "視為威脅，會抵制或公開批評"],
          ["產品護城河", "顧問專業 + AI = 混合智能", "純 AI，易被其他 LLM 追上"],
          ["法律風險", "低（最終決策在人類）", "高（幻覺、責任歸屬）"],
          ["市場規模", "全球數萬家 ESG 顧問公司", "數百萬家需要報告的企業"],
          ["產品定位", "顧問的第二大腦", "企業的自動報告機"]
        ]
      }
    },
    {
      "id": "target",
      "file": "docs/target.md",
      "title": "Target · 我們要 Build 什麼",
      "headline": "AI 輔助生成永續報告書，對象是顧問，時間從 40-80h → 8-15h",
      "valueProp": "用我們工具的顧問，能在同樣時間內產出品質更高、框架更完整、故事更動人的永續報告書，同時保留 100% 專業判斷與最終責任。",
      "outcomes": [
        "讓顧問變得更強、更快",
        "能接更多案子",
        "或做出更高品質的報告"
      ],
      "mantra": "我們要 Build 的不是『自動寫報告的機器』，而是『顧問的 AI 超能力放大器』 — Co-pilot，而不是 Replacement。"
    },
    {
      "id": "product_structure",
      "file": "docs/product_structure.md",
      "title": "Product Structure · MVP 三層架構",
      "headline": "輸入層 → 智能層 → 輸出層，外加顧問專屬功能",
      "layers": [
        {
          "name": "輸入層",
          "subtitle": "顧問最痛苦的部分",
          "items": [
            "上傳 Excel / PDF / ERP 報表 / 供應鏈問卷 / 舊報告",
            "支援結構化資料 + 非結構化文件（RAG）",
            "自動抽取關鍵指標（碳排範疇 1-3、能源、用水、多樣性）"
          ]
        },
        {
          "name": "智能層",
          "subtitle": "AI 核心",
          "items": [
            "多框架即時對應（GRI + ISSB + 台灣指引 + CSRD 可切換）",
            "自動生成各章節初稿（董事會聲明、氣候策略、重大性議題、目標與績效）",
            "差距分析（Gap Analysis）：你缺哪些指標、哪些敘事不夠有說服力",
            "雙重重大性評估輔助",
            "風險與機會自動連結（TCFD 風格）"
          ]
        },
        {
          "name": "輸出層",
          "subtitle": "顧問最有價值的部分",
          "items": [
            "可編輯的 Word / Google Docs 版本（保留所有來源引用）",
            "自動生成視覺化圖表建議",
            "版本管理 + 審核軌跡（方便後續確信）",
            "顧問可一鍵『注入自己的專業觀點與案例』"
          ]
        },
        {
          "name": "顧問專屬功能",
          "subtitle": "護城河所在",
          "items": [
            "顧問公司知識庫（過去最好的報告、寫作風格、客戶案例上傳 → AI 學會『我們顧問的語氣』）",
            "多客戶儀表板",
            "團隊協作與審核流程"
          ]
        }
      ]
    }
  ],

  "strategicPivot": {
    "before": {
      "label": "舊定位 (pre-2026-05-25)",
      "framing": "通用型 Claude Code skill（任何人可安裝）",
      "audience": "個人 / 任何想寫 ESG 報告的人",
      "valueClaim": "把寫報告變成可重複 SOP",
      "businessModel": "Open source skill（無商業模式）",
      "moat": "SOP 結構化 + 領域知識"
    },
    "after": {
      "label": "新定位 (2026-05-25 onwards)",
      "framing": "顧問的 AI 超能力放大器（Co-pilot SaaS）",
      "audience": "ESG 顧問 / 顧問公司",
      "valueClaim": "40-80h → 8-15h，品質還更高，責任 100% 在顧問",
      "businessModel": "顧問公司 SaaS 月費訂閱",
      "moat": "顧問專業 + AI 混合智能 + 顧問公司 KB"
    },
    "implication": "既有 skill（8-Phase SOP + references）並未報廢 — 它是新產品『智能層』的原型核心，但對外論述需重新包裝，目標客戶從『個人使用者』改為『顧問公司的顧問』。"
  },

  "sprintStatus": {
    "current": {
      "id": "SP1",
      "title": "永續報告書 SKILL 在 Claude 環境的建構與優化",
      "phase": "done",
      "rating": "A-",
      "summary": "8 個 task 全 done；susr v0.1 已部署、GitHub 公開、端到端跑通力麗 5364 案例。",
      "tasks": [
        { "id": "SP1-001", "title": "Skill 骨架建構", "status": "done" },
        { "id": "SP1-002", "title": "References 知識庫補完", "status": "done" },
        { "id": "SP1-003", "title": "Sub-skill 整合（docx/xlsx/pptx/pdf）", "status": "done" },
        { "id": "SP1-004", "title": "端到端試做：力麗 5364", "status": "done" },
        { "id": "SP1-005", "title": "部署到 ~/.claude/skills/", "status": "done" },
        { "id": "SP1-006", "title": "命名策略（susr vs sustainability-report）", "status": "done" },
        { "id": "SP1-007", "title": "GitHub 公開準備", "status": "done" },
        { "id": "SP1-008", "title": "External verification（WebSearch 批次）", "status": "done" }
      ],
      "surprise": "力麗 2023 是台灣中型 TPEx 上市公司的『反向示範』典型 — 試做版本相對實際版本是全方位升級。examples 從『驗證 SOP』升級為『gap-closing 教材』，成為產品差異化素材。"
    },
    "backlog": {
      "id": "SP2-candidate",
      "title": "SP2 候選 backlog（SP1-004 walkthrough §3 衍生）",
      "items": [
        "SKILL.md Phase 0 工具依賴分級補強",
        "phase2 PDF binary fallback + 資本額 MOPS 硬規則",
        "materiality 議合方法決策樹",
        "Phase 5 補食安 / 隱私 / 在地三個示範章節",
        "Phase 6 真實環境實機 build 驗證（跨平台字型 / 圖表 / 中文）",
        "加碼 2 家不同產業（金融 / 食品）驗證 SOP 泛化性"
      ]
    },
    "pivotBacklog": {
      "id": "PIVOT-aligned",
      "title": "戰略樞轉對齊 backlog（2026-05-25 後新增；含 gbrain 路線）",
      "items": [
        "✅ [done] gbrain survey → docs/research/gbrain-survey.md（4,800 字 + Mermaid + 8 risks）",
        "✅ [done] Layer 1 lint tests bootstrap（tests/lint/，9 個 test functions：references/ 使用時機段落、frontmatter、詞彙反查）",
        "✅ [done] Layer 2 scenario tests bootstrap（tests/scenarios/，lealea-5364.yaml expectations）",
        "✅ [done] GitHub Actions CI（.github/workflows/test.yml，push/PR 自動跑 pytest）",
        "🎯 **MVP v0.1 = Phase 3 重大性評估端到端**（Q1 決定，工程選型詳見 Q11-Q17 + CLAUDE.md §8）",
        "✅ [done] Step 1 R1: packages/susr/ scaffold + pyproject.toml + 完整 DDL（24 tables / 3 invariant views / 5 triggers，sqlite-vec 驗證通過）",
        "✅ [done] Layer 4 embedding benchmark harness: tests/benchmarks/embedding/ (22 queries / 38 corpus / BGE-M3+Qwen3+OpenAI 3 providers)",
        "✅ [done] websearch-pending audit: docs/research/websearch-pending-audit.md (4 全 resolved，建議 SP2 後 deprecate)",
        "✅ [done] user-guide skeleton: docs/user-guide/ (README + 4 philosophy + 3 scenarios + features template + 1 feature 範例)",
        "✅ [done] Step 1 R2 implementation：5 個並行 subagent 完成 brain CRUD + search/RRF + page_versions + timeline + 3 embedding providers + Anthropic LLM + MCP server + 9 tools + Layer 3+4 tests (158/158 pass)",
        "🥈 Step 2: 用 Option C 重組力麗 5364 example（entities/topics/ + projects/2025-sr/materiality-2025.md），跑 Phase 3 端到端",
        "🥉 Step 3: 把 references/*.md 整理進 packages/susr/susr/shared_kb/data/（pip ship；client repo 透過 snapshot copy 收到）",
        "🧪 Layer 4 benchmark 跑（user 自跑）：BGE-M3 vs Qwen3 vs OpenAI 在力麗 fixture 上 retrieval 對比，決定 default embedding",
        "📖 user-guide 後續補：跨年 restate 場景（restate action_type + 5% threshold；user-guide agent 標的缺口）",
        "🔱 ESG entity schema 已落地（R1 完成 17 entities + 19 edges enum）— R2 填 CRUD / lookup",
        "🛡️  Layer 3 連結性 invariant：DDL views 已建（v_chapter_completeness / v_core_topic_action_coverage / v_target_completeness）— R2 包成 Python invariant runner",
        "🏛️  iXBRL schema 預留（Q16）：DDL 已加 xbrl_concept 欄位（pages 表 nullable）；實作延後到金管會時程明朗",
        "🧰 MCP tools R2 實作：Phase 3 對應集（4 個 phase3 tools + 4 個 workspace ops，全為 NotImplementedError stub）",
        "🎨 LLMProvider extras 試水溫：R2 第一個真實 prompt 後 review 抽象是否要深化（Q17）",
        "🔬 Layer 4 benchmark 已備 harness — 跑完才能 close Q7/Q8 收斂",
        "🖥️  Phase B GUI 評估（PMF 後）：lightweight web vs Tauri vs Electron",
        "✍️  README.md 重寫：『顧問的 ESG 第二大腦 — sustainability brain for ESG consultants』",
        "🎯 顧問訪談（3-5 家獨立 / 小型顧問公司）：驗證 Claude Desktop + MCP 入口接受度",
        "🔬 競品分析：CSRone、SustainAI、Persefoni、Greenly + 與 gbrain 架構對照",
        "💼 商業模式收斂：open core? cloud sync 進階版? 付費部署服務?（待 docs/defeinition.md 由使用者親自更新）",
        "🧪 lealea 5364 重測 milestone 系列（per CLAUDE.md §8 / 使用者要求）：",
        "    a) Step 2 完成後：重組成 Option C 結構，原 Layer 2 scenario asserts 仍 pass",
        "    b) MVP v0.1 完成後：用 brain 重跑 Phase 3，產出與 SP1-004 試做結果對照（Layer 5 端到端）",
        "    c) Phase 4/5/6/7 每個 phase 實作完：該 phase 用 brain 跑力麗，產出與 SP1-004 對照（Layer 5 增量）",
        "    d) 每次 release 前：力麗作為 regression fixture 必跑",
        "📖 顧問面文件 docs/user-guide/（per 使用者要求 + §4.6.5）：",
        "    - README.md：susr 是什麼 / 為什麼為顧問而設",
        "    - philosophy/：co-pilot / double-materiality / auditable / anti-greenwashing 等核心設計哲學",
        "    - scenarios/：顧問痛點 → susr 解法（接新客戶 / 議題池怎麼選 / 客戶問為何用這排放因子 等）",
        "    - features/：每個 feature 三段式（這是什麼 / 何時用 / 為何這樣設計），邊實作邊寫"
      ]
    }
  },

  "openQuestions": [
    {
      "id": "Q1",
      "topic": "MVP 第一刀",
      "question": "所有架構決策收斂後，MVP v0.1 端到端切在哪個 Phase？",
      "options": [
        "Phase 3 重大性評估端到端（用 Option C + susr-brain 最小核心 + Claude Desktop + lealea fixture）",
        "Phase 1-3 串連（scoping + research + materiality）",
        "Phase 3 + Phase 7 gap analysis（兩端對照式 demo）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — MVP v0.1 = Phase 3 重大性評估端到端。理由：(1) susr ↔ gbrain 差距最大、價值密度最高；(2) 顧問痛點集中（雙軸評分 + 議合佔 30%+ 工時）；(3) Output 是 deliverable，客戶端可見易驗證；(4) 不依賴 Phase 4 GHG 引擎或 Phase 6 文件組裝（最複雜）；(5) 力麗 5364 phase3-materiality.md 13KB 完整 fixture 已備。成功指標：顧問可在 Claude Desktop 對 lealea 跑完 Phase 3、產出雙軸 + 矩陣 + IRO 對應，通過 Layer 2 scenario test。詳見 CLAUDE.md §8。"
    },
    {
      "id": "Q2",
      "topic": "技術交付形態",
      "question": "繼續走 Claude Code skill，還是另起 Web SaaS？",
      "options": [
        "skill：開發快、依賴 Claude Code 使用者基數",
        "Web SaaS：才能真正做顧問 KB / 多客戶儀表板 / 團隊協作",
        "雙軌：skill 當開源 lead-gen，SaaS 當商業化主體"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 參考 gbrain（github.com/garrytan/gbrain）路線：local-first、Markdown + Postgres backing、MCP-native，不先做 web SaaS。CLAUDE.md §8 有完整演進註記。"
    },
    {
      "id": "Q3",
      "topic": "首批顧問共創夥伴",
      "question": "找誰當 design partner？台灣 / 海外 / 大型四大 / 獨立顧問？",
      "options": [
        "獨立顧問或小型顧問公司（決策快、痛點明顯、付費意願需驗證）",
        "中型本土顧問公司（規模化案件、團隊協作真實需求）",
        "四大會計師事務所永續組（背書強，但流程慢、客製多）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 鎖定獨立顧問 + 小型顧問公司。理由：決策快、痛點具體、與 local-first 形態（Q2）相容（不需多人協作 infra 就能起步）。"
    },
    {
      "id": "Q4",
      "topic": "資料邊界與隱私 / Workspace 結構",
      "question": "顧問本機如何隔離多 client + consultant KB 怎麼跟 client KB 邊界？",
      "options": [
        "Per-client 獨立 git repo（最強隔離） + 單向闘 consultant-kb → client",
        "單一 workspace repo + client folder（簡單）",
        "Workspace + per-client submodule（混合）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — (1) Per-client 獨立 git repo，可推到不同 remote（含 client 自有 git）。(2) 單向闘：consultant-kb → client 可讀；反向需手動 anonymize + reviewer 審核 + 顯式 commit。Client 之間絕不互通。MCP tools 層分開暴露 read_consultant_kb 與 promote_to_kb（後者強制 confirm + audit trail）。⚡ 後續決策補強：DB 已定 SQLite + sqlite-vec（Q13）、shared-kb 改 snapshot copy 非 submodule（Q12）。仍未決：.susr/db.sqlite 細部 schema、跨 client 匿名複用合規邊界。詳見 CLAUDE.md §8。"
    },
    {
      "id": "Q5",
      "topic": "AI 模型策略",
      "question": "綁定 Claude 還是模型不可知（model-agnostic）？",
      "options": [
        "綁定 Claude（與 skill 路線一致，深度整合）",
        "Anthropic 為主 + OpenAI/Gemini 備援",
        "完全模型不可知（多增工程成本）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 階段式策略。Phase A（現在→PMF）：基於 Claude Desktop + MCP，方便不擅長 agent CLI 的顧問學習使用；GTM 短期綁定 Claude 生態加速 PMF。Phase B（PMF 後）：發展自家 GUI（lightweight web / Tauri）+ 支援 multi-agent CLI（Claude Code / Cursor / Windsurf），模型不可知化。工程紀律：所有 LLM 呼叫從 day 1 走抽象層，prompt 與 model-specific syntax 隔離。Embedding 模型獨立決策（見 Q7 / Q8）。"
    },
    {
      "id": "Q6",
      "topic": "gbrain 採用方式",
      "question": "Fork、純參考、還是 import as dependency？",
      "options": [
        "Fork gbrain 改名 susr-brain（深度客製，但繼承所有未實作的招牌功能坑）",
        "純參考設計理念，自己重寫（學習已驗證可行的架構，純淨 codebase）",
        "Import as dependency（susr 專注 ESG domain layer，gbrain 當儲存/檢索層）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 採 Plan B（純參考、自己重寫，使用者選擇覆蓋 agent 推薦的 Plan C）。使用者原話：『學習人家已經大量驗證可行的架構』。理由：gbrain spec-impl gap（招牌功能僅存於 markdown 指令未實作）= 工程風險；它驗證可行的架構模式（pgvector + hybrid search + RRF + page_versions + MCP）才值錢。Plan B 吸收後者規避前者。代價：多一層工程，但組件都有現成 OSS（pgvector / Postgres FTS / RRF 數學十行 / MCP 官方 SDK），可控。詳見 CLAUDE.md §8。"
    },
    {
      "id": "Q7",
      "topic": "個資與 embedding 合約風險",
      "question": "顧問把客戶員工薪酬/勞檢/客訴 ingest，embedding 送雲端違反 NDA。怎麼處理？",
      "options": [
        "全本地 embedding（BGE-M3 / Qwen3 / Ollama）— 品質可能差、運算需 GPU",
        "二段式 pipeline：敏感資料本地、非敏感雲端（顧問手動分類）",
        "client-level 設定：每個 client repo 可選 embedding provider（預設本地）",
        "純雲端 + 客戶端 NDA 補強（速度快，但合約風險仍在）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 預設本地 embedding（BGE-M3 或 Qwen3，跑 Layer 4 benchmark 選 default）；client-level 設定 _client.md frontmatter 標 embedding_policy: local/cloud/twostage，顧問可在客戶明確授權下改雲端。技術隔離為主、合約補強為輔。詳見 docs/research/step1-spec.md §5.3。"
    },
    {
      "id": "Q8",
      "topic": "中文 ESG 術語 embedding 品質",
      "question": "中英混雜 ESG 術語（「雙重重大性」「IRO」「Scope 3 類別 11」「GRI 305-1」）retrieval 品質要怎麼驗證？",
      "options": [
        "用力麗 5364 跑 Layer 4 benchmark（BGE-M3 vs Qwen3 vs OpenAI 三模型）",
        "等到 Phase 3 試做時順便驗（風險：太晚發現）",
        "直接 default 一個跳過驗證"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — Layer 4 跑 BGE-M3 + Qwen3 雙模型 benchmark（OpenAI 列對照組），用力麗 5364 phase3-materiality 當 fixture。預設先用 BGE-M3（成熟 + multi-vec），benchmark 完依結果換或維持。Hybrid search 同時跑 FTS5 trigram 走 BM25 path — BM25 對 ESG 編號類查詢（GRI 305-1 / Scope 3 類別 11 / ISSB S2 §29）特別關鍵。FTS5 trigram 中文精度若不足，benchmark 後評估 jieba tokenizer 退路（會破壞零安裝賣點）。詳見 step1-spec.md §5.4 + §10 風險 4。"
    },
    {
      "id": "Q9",
      "topic": "Client 內部架構（年度循環）",
      "question": "永續報告書是年度循環、client 是持續關係，client repo 內部怎麼分層？",
      "options": [
        "Option A: 純 project-based（簡單但跨年重複）",
        "Option B: 純 entity-centric（gbrain 哲學極致，deliverable 邊界模糊）",
        "Option C: entities + projects 混合（常駐實體 + 年度交付 + 跨年 sourcedocs）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 採 Option C 三層結構。entities/（topics, stakeholders, governance, kpis, targets — 跨年常駐，gbrain entity-as-page）+ projects/（每個 = 一個年度 deliverable，可含非報告書案如盤查/CDP/SBTi）+ sourcedocs/（按年歸檔，跨 project reuse）。新年度報告 = cp -r baseline + 改 framework_version + 議題 / KPI 加新年 assessment + chapters fork。完美對應 gbrain page_versions + restatedFrom edge。詳見 CLAUDE.md §8。"
    },
    {
      "id": "Q10",
      "topic": "測試紀律",
      "question": "現在 bootstrap 測試？採哪幾層？hard rule 寫進哪？",
      "options": [
        "Layer 1 + Layer 2 今天 bootstrap；hard rule 寫進 CLAUDE.md 主條文",
        "全部等 susr-brain Step 1 一起 TDD",
        "只寫 lint（Layer 1），scenario 後補"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — Layer 1 lint + Layer 2 scenario 今天 bootstrap，pytest 為框架。Hard rule 寫進 CLAUDE.md §6.1：『任何宣稱 feature 必有對應測試 — 沒測試的招牌功能不能寫進對外文案』。用 4 subagent 並行 dispatch（tests/ scaffold + Layer 1 lint + Layer 2 scenario + GitHub Actions CI）。Layer 3-4 隨 susr-brain Step 1 同步；Layer 5 後期。直接服務 Definition §4 信任與驗證 — 對使用者誠實的前提是先對自己誠實。詳見 CLAUDE.md §6 + §8。"
    },
    {
      "id": "Q11",
      "topic": "語言選擇",
      "question": "susr 核心 package 用什麼語言？",
      "options": [
        "Python — ESG 領域生態最強",
        "TypeScript — 與 gbrain 1:1 對應 + MCP DX",
        "Python core + TS MCP — 兩邊都要的混合"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — Python。理由：ESG 80% 硬骨頭在 pandas/openpyxl/PDF/排放模型 — Python 生態無可取代；與 pytest 連貫；Plan B 下不必為 gbrain TS 對應綁住；MCP SDK Python 完整。工具：uv + Python 3.11。詳見 CLAUDE.md §8 決策 1。"
    },
    {
      "id": "Q12",
      "topic": "Repo 結構",
      "question": "Mono-repo / multi-repo / hybrid + shared-kb 怎麼放？",
      "options": [
        "全 mono-repo + 單一 susr package + shared-kb 內含 + snapshot copy 進 client repo",
        "Hybrid: mono-repo + shared-kb 獨立 repo（submodule）",
        "Full multi-repo split"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 全 mono-repo（多次自我修正）。原本提案的「shared-kb 獨立 repo」reasoning 錯誤（倒果為因 — submodule 是手段不是需求）。shared-kb 留 mono-repo 內、跟 susr package 一起 pip ship；client repo 收到的是 snapshot folder（不是 submodule）。顧問零 git submodule 認知負擔，client repo 仍自包含可審計。同時 packages 結構從 3 個（brain/mcp/cli）簡化為 1 個（susr，內部模組化），cli 待 post-MVP 再說（YAGNI）。詳見 CLAUDE.md §8 決策 3+4。"
    },
    {
      "id": "Q13",
      "topic": "儲存引擎",
      "question": "DB 用 Postgres / SQLite / DuckDB / LanceDB？",
      "options": [
        "SQLite + sqlite-vec + FTS5（零安裝）",
        "Postgres + pgvector（與 gbrain 對齊，但要 Docker）",
        "DuckDB（OLAP 強但 OLTP/retrieval 弱）",
        "LanceDB（vector-first 但 FTS 弱）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — SQLite + sqlite-vec + FTS5。使用者原話：『得考慮 zero postgres，他們沒辦法搞 docker』。完全消除顧問安裝痛點：sqlite3 是 Python stdlib、sqlite-vec 是 pip extension。FTS5 內建讓 hybrid search 拿來就用。susr 場景負載（幾千-幾萬 pages）遠低於 SQLite 上限。Brain 介面層保持抽象，未來團隊版需共用 DB 時可換 Postgres。詳見 CLAUDE.md §8 決策 2。"
    },
    {
      "id": "Q14",
      "topic": "Skill ↔ Brain 整合",
      "question": "Skill 與 brain 在 MVP 怎麼相處？",
      "options": [
        "B 並行獨立（MVP）",
        "A Skill 自動 detect brain MCP server 並整合",
        "C 廢掉 skill 全走 brain"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — B 並行獨立。Skill 繼續服務 Claude Code 對話（純 SOP guidance）；brain 服務 Claude Desktop / Cursor / Windsurf（MCP tools）。兩條路徑獨立、不互引用。MVP 簡單；既有 skill 不動；brain 專心做好 Phase 3。PMF 後再評估整合。詳見 CLAUDE.md §8 決策 5。"
    },
    {
      "id": "Q15",
      "topic": "顧問安裝 UX",
      "question": "顧問從零到能用 susr 的 happy path？",
      "options": [
        "pip install susr + 設定 Claude Desktop MCP config（零 shell 指令、零 Docker）"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — pip install susr → 設定 Claude Desktop MCP config 一次 → 之後全部對話操作。CLI 命令延後（MCP tools 取代：create_client_workspace / health_check / update_shared_kb 等）。對齊 Q5 Claude Desktop 為 GUI 入口決策。詳見 CLAUDE.md §8 顧問 install UX 段。"
    },
    {
      "id": "Q16",
      "topic": "iXBRL / ESEF schema 預留",
      "question": "金管會 2028 強制 ISSB 可能要求結構化標記。susr-brain Step 1 要不要預留 xbrl_concept 欄位？",
      "options": [
        "預留空欄位（Step 1 加進 DataPoint/KPI schema，實作延後）",
        "完全不管（等真有需求再 schema migration）",
        "Phase 4 試做時再評估"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 預留空欄位，後續再做實作。Step 1 spike 在 DataPoint / KPI schema 上加 nullable xbrl_concept 欄位（不寫值、不驗證），避免 2028 法規生效時做 schema migration 影響歷史資料。實際填值機制 / iXBRL 渲染 / ESEF 驗證等實作延到金管會時程明朗後再做。對應 survey §8 risk #6。"
    },
    {
      "id": "Q17",
      "topic": "LLMProvider 抽象策略",
      "question": "Day-1 LLMProvider 抽象 vs YAGNI — Anthropic 高階特性（tool use / caching / extended thinking）怎麼處理？",
      "options": [
        "薄抽象（complete + tool_call）+ vendor extras 兩段式",
        "完整抽象（全 Provider Protocol 涵蓋所有特性，複雜）",
        "Day-1 不抽象，直接寫 anthropic SDK，未來再 refactor"
      ],
      "owner": "decided",
      "decision": "✅ 2026-05-25 — 薄抽象 + vendor extras 折衷。基礎介面 LLMProvider.complete / stream / tool_call（90% 邏輯走抽象），高階特性走 provider.anthropic_extras.enable_caching() 之類 vendor-specific path。Day-1 必須抽象（對應 Q5 Phase B multi-agent 鋪路），但不過度設計。第一個真實 prompt 落地後 review 抽象層是否需深化。對應 step1-spec.md §10 風險 6。"
    }
  ],

  "docIndex": [
    { "path": "CLAUDE.md", "desc": "對 Claude Code 的最高原則 instructions（§6 測試紀律 + §8 Decisions Log）" },
    { "path": "docs/defeinition.md", "desc": "🔱 原則 1 — 永續報告書本質 + Co-pilot vs Replacement 對照" },
    { "path": "docs/target.md", "desc": "🔱 原則 2 — 我們要 build 什麼（顧問 + 40-80h → 8-15h）" },
    { "path": "docs/product_structure.md", "desc": "🔱 原則 3 — MVP 三層架構 + 顧問專屬功能" },
    { "path": "docs/sprints/SP1.md", "desc": "Sprint 1 紀錄（done）" },
    { "path": "docs/standards/skill-development.md", "desc": "Skill 開發標準（含 Orchestrator §9、Graceful Degradation §10）" },
    { "path": "tests/README.md", "desc": "🧪 測試紀律入口 — Layer 1+2 已 bootstrap，Layer 3-5 待" },
    { "path": ".github/workflows/test.yml", "desc": "🔁 GitHub Actions CI — push/PR 自動跑 pytest" },
    { "path": "skills/sustainability-report/SKILL.md", "desc": "智能層原型：8-Phase SOP 主入口（未來會包成 MCP tools）" },
    { "path": "examples/lealea-5364/walkthrough-notes.md", "desc": "端到端試做心得（反向示範教材意涵）" },
    { "path": "docs/research/gbrain-survey.md", "desc": "🔍 gbrain → susr 對應映射報告（2026-05-25，4,800 字 + Mermaid + 17 entities + 19 edges + 5 invariants + 8 risks）" },
    { "path": "README.md", "desc": "對外說明（⚠️ pre-pivot framing，待依 gbrain 路線重寫）" },
    { "path": "https://github.com/garrytan/gbrain", "desc": "🧠 外部參考：gbrain — Garry Tan（YC CEO）的 local-first AI knowledge system，susr 採 Plan C 以 import 方式使用" }
  ]
};
