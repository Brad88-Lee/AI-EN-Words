# Phase 0 通訊測試清單（依 HANDOFF §11.4、§12、§13）

狀態標記：✅ 已實測　⬜ 未做　👤 需要使用者操作

## A. 前置：GitHub 設定（👤，HANDOFF §11.5）
- ✅ Settings → Actions → General → Workflow permissions 為 **Read and write permissions**（ping 已能 push 到 `main`）
- ✅ 已建立標籤 `needs-human`、`skip-diff`（使用者自述，我未用工具核對）
- ✅ `ping.yml`、`pr_probe.yml` 已合併進 `main`（PR #3、#4；`workflow_dispatch`、`repository_dispatch` 只認預設分支上的 workflow）

## B. 環境清單（§11.4）
| 項目 | 結果 |
|---|---|
| 本對話容器（Claude Code 雲端 session）：git clone／push `claude/` 分支 | ✅ 已 push 成功 |
| 本對話容器：Python 3.13.18、git 2.43.0；`pip install emoji` 經 proxy 成功（emoji 2.16.0） | ✅ |
| **Claude 排程任務的環境** | ✅ 2026-11-01 實測（PR #6）：Python 3.11.18；`pip install emoji` 回報成功，但 `python3 -c 'import emoji'` 失敗（pip 與 `python3` 疑似不同直譯器，未查證）→ 一律用 `python3 -m pip install emoji`；git 2.43.0；可推 `claude/` 分支並開 PR |
| Codex 雲端 | ✅ 2026-11-01 實測：repo 在 `/workspace/AI-EN-Words`（cwd 是 `/workspace`，不是 repo）；Python 3.12.14；agent 預設無對外網路，推送／開 PR 會報 proxy 錯誤；網路全開放後可推 `codex/` 分支並開 PR（PR #7）。環境「額外允許網域」縮窄到 `github.com`、`api.github.com` 尚未測 |
| GitHub Actions runner | 部分：ping 與 pr-probe 在 `ubuntu-latest` 跑成功；Python 版本、`pip install emoji` 尚未在 runner 上測（Phase 1 要測）。Actions 註記：`ubuntu-latest` 標籤自 2026-10-19 起遷移到 Ubuntu 26，需確認 Python／emoji 相容 |
| 手機 GitHub app：看 Issue 推播、觸發 `workflow_dispatch`、對 PR 加標籤 | ⬜ 👤 |

## C. §12 五項未驗證事項
| # | 項目 | 做法 | 結果 |
|---|---|---|---|
| 1 | 喚醒 Claude 排程任務 | 使用者無 API；官方文件列三種觸發：Schedule（最短 1 小時）、GitHub event（PR／Release／Issue，需 Claude GitHub App）、API。**GitHub event 由 Actions 事件觸發是否可行：未測** | ⬜ |
| 2 | Codex 排程 | ✅ 可建立雲端排程（執行於雲端，頻率可選每天／自訂）。**從綁定 `AI-EN-Words` 環境的對話建立**才會在正確 repo 執行（唯讀測試與寫入測試皆成功）；獨立建立的排程曾跑到 `AI-Education-Video-Studio`。表單提示「雲端任務無法使用對話、專案、模型和推理設定」。最短間隔、喚醒機制：未測 | 部分 |
| 3 | 指定模型與思考程度 | Claude 排程：有模型選擇器，使用者回報 Sonnet 5.5 時選不到 effort（中）。Codex 排程：不能指定。兩邊回報檔 `MODEL:` 皆為自述，Codex 自述 GPT-6 與介面選的 GPT-6.1 Sol 中不一致 | ✅ 結論：不可控、不可信 |
| 4 | 手機 GitHub app 能否觸發 `workflow_dispatch` | 👤 Actions → ping → Run workflow | ✅ 手機**網頁版**可觸發（2026-11-01 14:51 +08:00）；GitHub app 本身未測 |
| 5 | 兩個 AI 的 App 開 PR 時的作者身分 | 讓 Claude、Codex 各開一個 PR，看 `pr-probe` 的 job summary（login／type） | 部分：Claude Code 對話 session 用 GitHub 工具開的 PR #3，作者是 `Brad88-Lee`／`User`（不是 bot）。**routine、Codex 未測**；作者名不能當白名單 |

## D. repository_dispatch 串接
1. 👤 Actions → ping → Run workflow（備註填「manual」）→ `test/ping.md` 應多一行 `event=workflow_dispatch`。
2. 觸發鏈：到網頁或用有權限的 token 送 `repository_dispatch` event_type=`ping`。預期 `test/ping.md` 依序多 3 行：`ping` → `ping-chain-1` → `ping-chain-2`。
3. 第 2 行、第 3 行不是人觸發的，若出現就代表「GITHUB_TOKEN 發出的 repository_dispatch 會觸發下一個 run」成立（HANDOFF §12 引用官方文件，這裡是實測）。
4. 若鏈只跑到第 1 行：總管步驟間要改用 PAT 或排程，要回頭改 HANDOFF §12。

## E. 結論欄（做完再填）
- 2026-11-01 實測（以 `main` 上 `test/ping.md` 與 Actions 紀錄為證）：
  - `workflow_dispatch`：手機網頁版與電腦網頁皆可手動觸發。
  - **`repository_dispatch` 串接成立**：手動 run（15:32:35）→ ping（15:32:43）→ ping-chain-1（15:32:52）→ ping-chain-2（15:33:02），後三筆 actor 皆為 `github-actions[bot]`，由前一個 run 用 `GITHUB_TOKEN` 送出。HANDOFF §12「不用 PAT」的說法成立；單一 `concurrency` 群組下連續 dispatch 沒有被丟掉。
  - **PR 作者身分不能當白名單**：Claude Code 對話 session 開的 PR #3、#4，`user.login=Brad88-Lee`、`user.type=User`。但 `head.repo` 等於 base repo、`fork=false`，可改用「同 repo 分支」把關（§9.1 待改）。routine、Codex 開的 PR 尚未測。
  - 尚未驗證：routine 喚醒方式、模型指定、routine／Codex 的環境與 PR 身分、GitHub app 手機版觸發。
- 2026-11-01 補充實測（Claude 排程、Codex 排程）：
  - Claude 排程任務開的 PR #6：作者 `Brad88-Lee`／`User`，同 repo 分支 `claude/…`。
  - Codex 開的 PR #7：作者 `Brad88-Lee`，commit 作者 `Brad`，分支 `codex/probe-3`（非 `claude/` 前綴）。第二次排程再推同一分支，PR 已存在而「新建失敗」，屬正常；PR 自動包含新 commit。
  - 三種來源（Claude 對話、Claude 排程、Codex）的 PR 作者全是 `Brad88-Lee`，**不能用作者辨識 AI**；`head.repo` 同 repo 則三者皆成立。
  - Codex 第一次推送／開 PR 遇 proxy 錯誤，重試後成功；原因未知（推測與剛發佈環境有關，未驗證）→ prompt 要求失敗時重試。
  - 過去 `main` 上有 ChatGPT 相關的直接 commit（`cbe70a7`），repo 目前無分支保護。
  - 未驗證：環境網路縮窄後是否仍可推送；Codex／Claude 排程重複執行穩定性；GitHub 手機 app 觸發；Actions runner 的 Python／emoji（`ubuntu-latest` 已遷移至 Ubuntu 26）。
