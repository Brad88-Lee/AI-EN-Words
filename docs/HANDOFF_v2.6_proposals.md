# HANDOFF v2.5 → v2.6 修改建議（Phase 0 實測後）

> 狀態：**建議，尚未套用**。HANDOFF 不在本 repo，請使用者審核後再改。
> 標記：✅ 已實測（GitHub 上可查證）　🔶 使用者回報／推測　⬜ 未驗證
> 證據來源：`test/ping.md`、PR #3～#7、`codex/probe-3` 分支、使用者截圖。

## 1. §12 喚醒方式：刪除「API trigger」前提（使用者沒有 API）
- 官方文件列三種觸發：Schedule（最短 1 小時）、GitHub event（Pull request／Release／Issue，需安裝 Claude GitHub App）、API。
- 建議：Claude 端先採 **Schedule 輪詢**（HANDOFF 原有備案）。**GitHub event 喚醒**（由 Actions 開 Issue 或加標籤觸發）為加速方案，⬜ 未測，尤其「`GITHUB_TOKEN` 產生的事件是否會被 Claude 收到」不知道。
- Codex 端：雲端排程可建立 ✅；最短間隔、能否被事件喚醒 ⬜。
- ✅ 總管步驟間用 `repository_dispatch` 串接成立（`GITHUB_TOKEN` 發出的 dispatch 會觸發下一個 run，ping → chain-1 → chain-2），不需要 PAT。

## 2. §9.1 作者白名單：改成「同 repo 分支」把關
- ✅ Claude 對話、Claude 排程、Codex 三種來源的 PR，作者全是 `Brad88-Lee`／`User`；Codex commit 作者是 `Brad`。作者無法辨識 AI。
- ✅ 三者的 `head.repo` 都等於本 repo（`fork=false`）。
- 建議把關條件：`head.repo == base repo`（擋 fork）＋回報檔 `ROUND`／`STAGE` 與 `state.json` 相符＋只改允許路徑。
- 建議在回報檔加欄位 `AGENT: claude | codex | human`，**僅作過濾**（`status=waiting` 時缺合法值 → 記為不合規交付、不計 attempt）。它是自述，不是驗證。
- 人工修檔維持 `needs_human`／`paused` ＋ `skip-diff` 標籤。

## 3. B（Codex）交付規則
- ✅ 網路開放時，Codex 可推 `codex/…` 分支並開 PR。分支前綴是 `codex/`，不是 `claude/`；§0 第 9 點與 §4.2 要允許 `codex/` 前綴。
- ✅ PR 已存在時再推同一分支，PR 會自動更新，Codex 再開 PR 會報「already exists」：prompt_B 要寫明「PR 已存在視為成功，不要當錯誤」。
- 🔶 第一次推送／開 PR 曾遇 proxy 錯誤，重試後成功：prompt_B 要求「失敗時等待後重試，最多 3 次」，並在回報檔記錄。
- 備案：若縮窄網域後 Codex 仍開不了 PR，改由 Actions 偵測 `codex/**` 推送後自動開 PR（需勾 Settings → Actions → General → Allow GitHub Actions to create and approve pull requests）。
- ⬜ 環境網路縮窄到 `github.com`、`api.github.com` 是否仍可用，尚未測。目前環境為全開放，**不應長期保留**。

## 4. §2 角色與模型：思考程度不可控
- Codex 雲端排程：表單寫明「雲端任務無法使用對話、專案、模型和推理設定」，B 的「GPT-6.1 Sol 中」無法由排程指定。
- Claude 排程：有模型選擇器；🔶 使用者回報選 Sonnet 5.5 時選不到 effort。Opus 5.5 是否有 effort ⬜ 未看。
- ✅ `MODEL:` 自述不可信（Codex 自述 GPT-6，介面為 GPT-6.1 Sol 中）。HANDOFF 已寫「只供記錄」，維持。
- 建議：§2 表格改成「期望值」並註明實際由平台預設決定；以輸出品質（總管驗證）而非自述判斷。

## 5. 環境與 prompt 修改
- Claude 排程：Python 3.11.18；`pip install emoji` 成功但 `import emoji` 失敗 → 指令一律 `python3 -m pip install emoji`，並在 prompt_A／C 的自檢段改寫。
- Codex：repo 在 `/workspace/AI-EN-Words`，cwd 為 `/workspace`（不是 repo）。prompt_B 第一步應 `cd /workspace/AI-EN-Words` 並確認 `git remote -v` 為本 repo，**不符就停止**。⬜ 在此結構下 `AGENTS.md` 是否被自動讀取未知，所以 §11.2 的「第二層保險」（prompt 第一句明寫讀 `AGENTS.md`）是必要的，不是選配。
- Codex 不需要 `emoji`（B 不跑腳本，§11.3），Codex 環境的 `pip install emoji` 可移除。
- ✅ Codex 排程要從「綁定 `AI-EN-Words` 環境的對話」建立；獨立建立的排程跑到了 `AI-Education-Video-Studio`（該 repo 留下 `phase0/probe-codex-20261101`）。建立排程後要先做唯讀檢查再放行寫入。
- Python 版本四處不同：Claude 3.11、Codex 3.12、本對話容器 3.13、Actions ⬜（`ubuntu-latest` 已於 2026-10-19 起遷移至 Ubuntu 26）。Phase 1 要在 runner 上實測 `check_*.py`。

## 6. §10 腳本現況
- ✅ 已完成：`check_batch.py` 移除 opencc、有 ERROR 時 exit 1、可讀 `vocab_####.json`；`check_extra.py --history` 可給目錄；連字號詞整詞比對、a/an 依字母名稱、zh 允許 1～4 個大寫字母（`tests/` 12 項單元測試）。
- ⬜ 未做：`diff_check.py`、`validate_report.py`、`error_signature.py`。
- 待統一：兩支腳本的大陸用語清單不一致；例句長度 prompt_A／C 寫 8～18 字、prompt_B 寫 8～16 字（§11.0 規定規則本文不改，需使用者決定）。
- `used_emoji.py`、`apply_b.py` 未改，未跑過真實資料。

## 7. 其他
- §1：字表是 7,875 字，另有 `unable`（#15）不在字表內；7,876 是資料庫加待生成的列數。
- §11.5：Workflow permissions 已設為 Read and write ✅；標籤 `needs-human`、`skip-diff` 已建 🔶（使用者自述）；「Allow GitHub Actions to create and approve pull requests」目前**未勾**，若採第 3 節備案需勾。
- ✅ 手機網頁版可觸發 `workflow_dispatch`；GitHub app 本身 ⬜。
- 🔶 `main` 上曾有 ChatGPT 相關的直接 commit（`cbe70a7`），repo 無分支保護。HANDOFF §9.4 說不設保護，但 AI 可直接寫 `main` 會繞過總管，建議 Phase 1 評估。

## 8. 仍未驗證（Phase 0 剩餘項目）
1. Claude GitHub event 觸發（及由 Actions 事件觸發）。
2. Codex 排程的最短間隔、被事件喚醒的可能。
3. 環境網路縮窄後 Codex 仍可推送。
4. Opus 5.5 是否可選 effort。
5. GitHub 手機 app 觸發 `workflow_dispatch`。
6. Actions runner 上的 Python／`emoji`。

## 9. 決定紀錄（2026-11-01，使用者）
| 項目 | 決定 | 備註 |
|---|---|---|
| §9.1 作者白名單 | **同意**改為「同 repo 分支」把關，加 `AGENT:` 簽名欄位 | 簽名只是過濾，不是驗證；不加時間（時間由 Actions 蓋章，回報檔已有 `REPORTED_AT`）。**已決定加 `ATTEMPT:`**（AI 抄寫 `state.json` 的 `attempt`），總管比對，不符記為過期交付、不計 attempt |
| B 的交付 | **同意**；加「失敗重試」（最多 3 次，回報檔記錄）、「PR 已存在視為成功」、允許 `codex/` 前綴 | |
| 模型與思考程度 | **同意**：§2 表格改為「期望值」，實際由平台預設決定 | |
| prompt_B | **同意**：第一步 `cd /workspace/AI-EN-Words`，確認 origin，不符就停止 | |
| Claude 腳本 | **同意**：一律 `python3 -m pip install emoji` | |
| 例句長度 | **統一為「約 8～18 個英文字」**：prompt_B 第二節的「8～16」改為「8～18」；`check_batch.py` 的 5～25 字 WARN 範圍另議 | 此為使用者明確授權的規則本文修改，覆蓋 HANDOFF §11.0 的「不改規則本文」 |
| Allow Actions to create PRs | 只在採用「Actions 自動開 PR」備案時才勾 | |
| 分支保護 | Phase 1 再評估 | |
| Phase 1 | **等使用者說開始**（`CLAUDE.md`、`AGENTS.md`、`state.json`、`jobs.md`、`vocab/` 切檔等） | |
| §12 事件喚醒測試 | **同意測試**；Claude 用 GitHub event（Issue opened），Codex 用 `@codex` 留言；workflow 為 `.github/workflows/wake_test.yml` | 結果待測，寫入 `test/PHASE0.md` |

以上決定尚未寫回 HANDOFF 與 prompt 檔（它們不在本 repo）；套用在 Phase 1 一併處理。
