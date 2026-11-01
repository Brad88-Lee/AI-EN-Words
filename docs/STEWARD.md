# 總管（steward）操作手冊

總管＝GitHub Actions 加 `scripts/steward.py`，不用 AI。AI 只交付「輸出檔＋回報檔」的 PR，只有總管能判定正確或錯誤、寫 `state.json`。
規格見 `HANDOFF.md` 與 `docs/HANDOFF_v2.6_proposals.md`；這份只寫怎麼運作、怎麼操作。

## 檔案
| 檔案 | 用途 |
|---|---|
| `.github/workflows/steward.yml` | 兩個入口：AI 的 PR（`pull_request_target`）、人工動作（`workflow_dispatch`） |
| `.github/workflows/stall_check.yml` | 每小時逾時偵測 |
| `scripts/steward.py` | 所有判斷與狀態機（可在本機測試：`tests/test_steward.py`） |
| `scripts/steward_finish.sh` | 提交並推送狀態、處理 PR／Issue |

安全：`pull_request_target` 讓 workflow 與腳本一律來自 `main`；PR 的檔案只當資料讀（checkout 到 `pr/`），不執行。AI 無法改 `.github/`、`scripts/`、`prompts/`（改了就被拒絕）。

## 一個 PR 的處理流程
1. 非本 repo 分支（fork）→ 關閉，不 checkout。
2. `validate-pr`（唯讀）：
   - 改到允許路徑以外 → **拒絕**；檔案屬於別的輪次／階段 → **過期交付**。
   - `status` 是 `needs_human`／`paused` 時，只接受 `AGENT: human` 的人工修檔，其他一律過期。
   - 回報檔：`AGENT` 不合法 → **拒絕**（不計 attempt）；`ROUND`／`STAGE`／`ATTEMPT` 與 state 不符 → **過期**（不計 attempt）。
   - 內容：A＝`check_batch`＋`check_extra`；B＝`validate_b`；C＝`check_batch`＋`check_extra`＋`diff_check`。任何 ERROR → **驗證失敗**（計 attempt）。
3. 通過 → `gh pr merge --squash`（綁定驗證時的 commit）→ `apply-result` 推進 `state.json`、寫 `jobs.md`、`master/`、`used_emoji.txt`、`metrics/rounds.csv`。
4. 失敗 → 先把 PR 的檔案與檢查報告複製進 `attempts/N####-X-try#/` 並推上 `main`，**再**關 PR。`attempt+1`；`attempt` 達 3 或錯誤簽章與上次相同 → `needs_human` 並開 Issue。
5. 時限 `DEADLINE_HOURS=3`（暫定，Phase 2 量測後定）。

## 復原機制（審查後補強）
- **不計 attempt 的交付**（fork、AGENT 不合法、過期、改到允許路徑外）：只要還在 `waiting`，總管會重設時限並**重新喚醒**；同一階段**連續 3 次**就轉 `needs_human` 並開 Issue（`noncount_streak`）。
- **`continue` 一律有效**：不論目前是 `waiting`／`paused`／`needs_human`，都重設時限、清掉 `open_issue`（關掉停滯／人工處理 Issue）、重新喚醒。
- **任何驗證通過**都會清掉 `open_issue`。
- **symlink**：PR 內的輸出檔或回報檔若是 symlink（或上層目錄是 symlink），直接拒絕，不讀、不複製。
- **人工修檔失敗**寫到 `attempts/N####-X-human-<時間>/`，不覆寫 AI 那次的 `try#` 目錄。
- 人工修檔的回報檔：`AGENT: human`，且 **`ATTEMPT` 必須等於 `state.json` 的 `attempt`**，否則被判過期。

## 喚醒
- **Claude（A、C）**：總管把 state 推進到 A 或 C 時，開一個 Issue，標題 `[wake-claude] N#### A attempt 1`。Claude 的排程任務用「GitHub 事件：議題已開啟」觸發，篩選用「標題**包含** `[wake-claude]`」（Phase 0 實測：不能用「開頭為」）。Claude 被叫醒後**仍然只看 `state.json`**，忽略 Issue 內容。
- **Codex（B）**：不能被 Actions 叫醒（`github-actions[bot]` 的 `@codex` 留言連接器不回應）。用 Codex 雲端排程輪詢；排程要「從綁定 `AI-EN-Words` 環境的對話」建立。
- 備案：Claude 另設每小時排程輪詢；`stall_check` 逾時會開 Issue 通知你。

## 人工動作（Actions → steward → Run workflow）
| 動作 | 做什麼 |
|---|---|
| `continue` | `status=waiting`、重設時限、重派（基礎設施問題排除後；解除 `paused`／`needs_human`） |
| `redo` + `stage` | 目前輪從該階段重來：該階段與下游檔案清進 `attempts/N####-rollback-…/`，`attempt=1`。`round` 可填 `skipped_rounds` 內的輪（做完會回到原本的輪） |
| `skip` | 跳過本輪（記 `skipped_rounds`），進入下一輪；連續 2 輪需人工 → `paused` |
| `imported` + `batch` | 在 `master/IMPORTED.md` 記一筆「批 ## 已匯入」 |

人工修檔：自己（或叫 AI）開 PR，回報檔 `AGENT: human`，只在 `needs_human`／`paused` 時有效。AI 代修**一定跑 diff**（要在回報檔結構化區塊列出改了哪些 path）；親手改幾個欄位可加標籤 `skip-diff`（仍跑 `check_batch`／`check_extra`）。

## 初次啟動（Phase 2 之前）
`state.json` 現在是 `status=paused`。你要先做：
1. **Claude**：建立排程任務（`claude.ai/code/routines`）：repo `AI-EN-Words`、環境 Default、觸發＝GitHub 事件「議題：已開啟」＋標題「包含」`[wake-claude]`、模型 Sonnet 5.5（A）。prompt 第一句：`先讀 repo 根目錄的 CLAUDE.md 並依其行事。`（C 要不要換 Opus 5.5 見 HANDOFF §2，同一個任務同模型；要分開就建兩個任務）。建議再加一個每小時的排程觸發當備案。
2. **Codex**：從綁定 `AI-EN-Words` 環境的對話建立排程，prompt 第一句：`先 cd /workspace/AI-EN-Words，讀 AGENTS.md 並依其行事。`；環境網路要能連 `github.com`、`api.github.com`（Phase 0 是全開放測試，縮窄尚未驗證）。
3. 確認 Settings → Actions → General → Workflow permissions 為 Read and write。
4. 跑 `continue`，觀察第 1 輪（Phase 2：1 輪 → 3 輪 → 10 輪…）。

## 已知限制
- Actions 流程沒有在真實 GitHub 上跑過，只有 `steward.py` 的單元／情境測試（`tests/test_steward.py`）。第一次執行請盯著 Actions 頁與 `jobs.md`。
- `gh pr view --json files` 最多回 100 個檔案；正常交付只有 2 個檔案，沒問題。
- 合併後 state 推送失敗：workflow 會失敗並開 `[總管失敗]` Issue；檢查 `state.json` 後以人工動作處理。
- 時限、重試次數、批檔合成規則都寫在 `scripts/steward.py` 開頭的常數與函式。
