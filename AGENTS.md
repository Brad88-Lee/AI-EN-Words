# AGENTS.md：B（校正）的工作規則（給 Codex）

你只做 B。規格全文見 `HANDOFF.md`；Phase 0 實測後的修改與使用者決定見 `docs/HANDOFF_v2.6_proposals.md`（第 9 節，優先）。

## 通用規則
- 一律使用台灣繁體中文與台灣慣用語；專有名詞、程式碼保留原文。
- 本 repo 是 **Public**：不得寫入任何密碼、token、API key。
- **不要在 PR 標題、說明、留言裡寫 `@codex` 或其他 `@` 提及**（會誤觸發連接器）。
- 「AI 自己說正確」不算正確；只有總管（GitHub Actions 與腳本）能判定。

## 工作目錄
Codex 雲端的預設目錄是 `/workspace`，**repo 在 `/workspace/AI-EN-Words`**（`/workspace` 本身不是 git repo）。
1. 先 `cd /workspace/AI-EN-Words`。
2. 執行 `git remote -v`。origin 不是 `https://github.com/Brad88-Lee/AI-EN-Words.git` 就**立刻停止**並回報，不得對其他 repository 做任何事。
3. 本檔位於 repo 根目錄；若你的預設目錄不是 repo，請明確讀 `/workspace/AI-EN-Words/AGENTS.md` 與 `/workspace/AI-EN-Words/prompts/prompt_B.md`。

## 每次醒來的步驟
1. 從最新 `main` 開始（`git fetch origin main`，分支從 `origin/main` 切出）。
2. 讀 `main` 的 `state.json`。**只有同時符合** `stage=B`、`status=waiting` 才動作；否則回報「無待辦」並結束，不要產出任何檔案、不要開 PR。
3. 讀 `prompts/prompt_B.md`，依其指示作業。
4. `attempt` 大於 1：先讀 `last_failure_report` 指向的檔案，修正「必修」段列出的問題。
5. 分支名稱 `codex/N####-B`（`####` 是 `round`）；PR 開到 `main`，標題 `N#### B 交付`。
6. 無法完成：**仍要開 PR**，回報檔寫 `GATE-B: FAIL｜原因`，輸出檔可缺。
7. `git push` 或開 PR 遇到網路錯誤（proxy、connection）：等待約 30 秒後重試，最多 3 次，並在回報檔記錄。PR 已存在視為成功，不要當錯誤。

## 只能新增或修改這些檔案
`out_B/N####B_vocab_####.json`、`reports/N####_B_done.md`。
其他任何檔案一律不可動（含 `state.json`、`jobs.md`、`used_emoji.txt`、`master/`、`attempts/`、`reports/check/`、`vocab/`、`history/`、`prompts/`、`scripts/`、`tests/`、`docs/`、`.github/`、`HANDOFF.md`）。

## 回報檔
必含 `ROUND`、`STAGE: B`、`AGENT: codex`、`ATTEMPT`（抄 `state.json` 的 `attempt`）、`OUTPUT`、`GATE-B`。格式見 prompt_B 文末。B **不需要**執行檢查腳本，也不需要安裝任何套件。
