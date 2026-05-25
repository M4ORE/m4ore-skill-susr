# Layer 4 — Embedding Benchmark Harness

> **目的**：在 susr 真實使用情境（顧問用中文 + 框架代碼 + ESG 術語查永續知識庫）下,比較三組候選 embedding model 的 retrieval 品質,作為 `packages/susr/` 預設模型決策依據。

## 為什麼這個 benchmark 重要

`CLAUDE.md §8` 兩個未決問題在此收斂:

- **Q7（個資合約風險）**:顧問的客戶資料 ingest 後若 embedding 送 OpenAI 是 DPA 風險。預設**本地 embedding** 可一筆消除阻力 → 候選 `BGE-M3`、`Qwen3-Embedding-0.6B`。
- **Q8（中文 ESG retrieval 品質)**:`docs/research/step1-spec.md §5.4` 推測本地模型表現足夠,但**未實測**;不測就寫進 README/dashboard 違反 `CLAUDE.md §6.1` hard rule(任何宣稱 feature 必有對應測試)。

本 harness 跑出來的數字 → 寫進 `docs/research/embeddings-bench-v0.md` → 決定 `susr/embeddings/__init__.py` 的預設 provider。

## 候選模型

| Provider | 來源 | Dimension | Hosting | 模型大小 | 選擇理由 |
|----------|------|-----------|---------|---------|---------|
| `bge-m3` | BAAI/bge-m3 | 1024 | local | ~570 MB | C-MTEB 中文長期領先;多語訓練;Apache-2.0 |
| `qwen3-embedding-0.6b` | Qwen/Qwen3-Embedding-0.6B | 1024 | local | ~1.2 GB | 2025 新一代,中文+程式碼;MIT(確認 license);與 Claude 生態解耦 |
| `openai-text-embedding-3-large` | OpenAI API | 3072 | cloud | — | 業界 baseline;但是要 OPENAI_API_KEY + DPA |

**注意模型下載大小**:首次跑 local provider 會自動從 HuggingFace 拉模型到 `~/.cache/huggingface/`。**估算 ~1.8 GB**,首次跑請預留時間 + 頻寬。雲端 provider 不下載但會發 API 請求(成本見下)。

## 如何跑

```bash
# 1. 安裝依賴(在 repo root)
pip install -r tests/benchmarks/embedding/requirements.txt

# 2. (cloud provider 才需要)export OPENAI_API_KEY
export OPENAI_API_KEY=sk-...

# 3. 跑全套 benchmark
python -m tests.benchmarks.embedding.run_benchmark

# 4. 只跑特定 provider
python -m tests.benchmarks.embedding.run_benchmark --providers bge-m3,qwen3

# 5. 限縮 queries (debug)
python -m tests.benchmarks.embedding.run_benchmark --queries-limit 5
```

## 評估指標

| 指標 | 定義 | 為什麼這個指標重要 |
|------|------|----------------|
| **Recall@1** | top-1 是否命中 expected_topics 任一個 | 顧問問一句話,首選答案對不對 |
| **Recall@5** | top-5 內覆蓋率 | hybrid search 第一頁的覆蓋面 |
| **Recall@10** | top-10 內覆蓋率 | RAG context window 邊界 |
| **MRR** | Mean Reciprocal Rank,1/(命中名次) 平均 | 對「順序」敏感;比 Recall 更嚴 |
| **latency_ms / query** | 每 query 嵌入 + 檢索的 wall-clock | 顧問互動體感;cloud round-trip vs local CPU/GPU |

額外做 **by-category 拆解**(`exact_code` / `semantic` / `mixed_zh_en` / `fuzzy`),因為四類查詢對 embedding model 的考驗點不同:exact_code(GRI 305-1)應該 FTS5 BM25 也能搞定、semantic(公司用水 vs water consumption)才是 embedding 真正勝出處。

## 結果輸出

跑完後在 `results/` 下:

```
results/
├── bge-m3.json            ← 每 query 的 hit list + scores + latency
├── qwen3-embedding-0.6b.json
├── openai-text-embedding-3-large.json
└── summary.md              ← 三模型總比較 + by-category 拆解(人類讀的)
```

`summary.md` 一行決策:**選 X 作為 susr v0 預設 embedding,理由是 ...**。把這行手動帶入 `docs/research/embeddings-bench-v0.md`。

## 不在範圍

本 harness 是 **spike**(`CLAUDE.md §0.2`),不是 production grade:

- ❌ 不自動下載模型(交由 sentence-transformers / HF 第一次跑時懶載入)
- ❌ 不驗證 BGE-M3 / Qwen3 模型 hash(信任 HF mirror)
- ❌ 不做超參數調(只跑各 provider 預設配置;reranker / dimension reduction 留未來)
- ❌ 不寫進 CI(模型太大、API key 要錢;本機跑、結果手動 commit 即可)
- ❌ 不跑 corpus > 1000 條(corpus.yaml 30-50 條足以 spike;real benchmark 等真有資料再說)

## 預估時間 / 成本

| Provider | 一次完整 run(~25 queries × ~40 corpus) | 成本 |
|----------|----------------------------------------|------|
| bge-m3 | M1 Mac ~30s / Intel CPU ~2-3 分 | $0(local) |
| qwen3-embedding-0.6b | 同上 ×1.5(模型較大) | $0(local) |
| openai-text-embedding-3-large | ~5-10s(API I/O) | < $0.01(text-embedding-3-large $0.13/1M tokens,本 fixture < 30k tokens) |

整套跑 < 5 分鐘 + < 1 美分。
