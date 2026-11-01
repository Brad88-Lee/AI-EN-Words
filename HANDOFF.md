# HANDOFF v2.5：AI-EN-Words 自動多輪生成流程（給 Claude Code）

> **2026-11-01 補註（Phase 1）**：本檔為 v2.5 原文。Phase 0 實測後的修改建議與使用者的決定紀錄見 `docs/HANDOFF_v2.6_proposals.md`（第 9 節），其「已決定」項目優先於本檔；Phase 1 結束後整併為 v2.6。`prompts/` 內的 prompt 已套用其中與 prompt 有關的決定。

> 版本：2026-11-01 v2.5（v2.4 回歸檢查：D 定義釐清、人工修檔改走 PR 並可選是否跑 diff、使用者 PR 只在 needs_human 時有效、已通過輪次不回頭重跑、失敗 PR 先複製再關閉、回報檔寬鬆解析）
> 標記：【確認】使用者已明確同意　【已驗證】實際讀過原始碼／官方文件／算過　【未驗證】尚未實測，不可當事實
> 本檔是規格，不含可執行程式碼。本檔與其他文件衝突時，以本檔為準。

---

## 0. 工作規則（Claude Code 必須遵守）

1. 一律台灣繁體中文，禁簡體與大陸用語；專有名詞、程式碼保留原文。
2. 優先官方來源；與實測衝突時要指出差異。
3. 不確定先查證，不猜、不假設功能存在；查不到就說不知道。
4. 預設精簡；使用者要求完整版時，主動指出風險與易忽略處。
5. **使用者說「動手開始寫」之前，不寫任何程式／workflow／腳本，不 commit、不 push。** 先討論與分析。
6. 會大量消耗 usage／token 前（批次多輪、大量呼叫、長時間排程）先確認再做。
7. 每次提方案都附「建議 Model 與 Thinking 程度」。
8. Repo 為 **Public**：不得放任何密碼、token、API key、管理密碼、Supabase／Lovable 金鑰；能不用 secret 就不用。
9. Claude routine 預設只能推 `claude/` 開頭分支，**保留此限制**。
10. 「AI 自己說正確」不算正確；只有總管（Actions＋腳本）能寫正確／錯誤。

---

## 1. 目標與現況

目標：把剩餘 5,881 個英文單字，以每輪 50 字，自動走 A→B→C（含 D 程式檢查）閉環，產出可匯入 Lovable 的最終 JSON。本流程**不碰資料庫**，匯入由使用者手動在 Lovable 後台做。

【已驗證】
- 字表共 7,876 字；已匯入 1,995 字（測試 50、第1批 550、第2批 445、第3批 450、第4批 500）。
- 待生成：序號 **1996**（"switch"）到 **7876**（"woods"），共 **5,881 字 → 118 輪**。
- `vocab_version`=2；emoji 為 null 約 1,189 字（另案，不在本流程）。

GitHub：https://github.com/Brad88-Lee/AI-EN-Words 【確認】Public、分支 `main`、目前只有 README.md。repo 只放單字內容，授權不是疑慮。

---

## 2. 角色與建議模型

| 角色 | 工作 | 誰做 | Model／Thinking |
|---|---|---|---|
| 總管 | 切檔、驗證、記錄、派工、重試、停滯偵測、開 Issue | **不用 AI**：GitHub Actions＋腳本 | 無 |
| A 生成 | 讀 vocab 生成 50 字 | Claude Code 雲端 routine | Sonnet 5.5 **中** |
| B 校正 | 只出問題清單 | **Codex 雲端** | GPT-6.1 Sol **中**（截圖顯示目前「輕度」，使用者要改） |
| C 驗證套用 | 驗證 B 的問題、套用、輸出最終檔 | Claude Code 雲端 routine | Opus 5.5 **低**；若仍整份輸出且出錯，升中 |
| D 程式檢查 | **仍然存在**：所有由總管執行的程式檢查（check_batch、check_extra、diff）統稱 D。D 在 A 與 C 的驗證內執行，不是 `state.stage` 的一個值，因為沒有 AI 要等它 | Actions | 無 |
| 規格與實作（Claude Code 本身） | 設計、寫 workflow | — | Sonnet 5.5 中；審查矛盾用 Fable 5.1 |

【已驗證，使用者截圖】Codex 雲端模型選單：GPT-6.1 Sol、GPT-6 Astra、GPT-6.1 Terra、GPT-6 Sol、GPT-6 Luna、GPT-5.6 Sol。
【未驗證】routine 能否分別指定模型與思考程度。**取捨**：A、C 用不同模型需兩個 routine，每個 routine 每小時醒一次、不是自己的階段就空跑，空跑也算 run，會吃每日上限；用**一個 routine 同時負責 A 與 C**（`CLAUDE.md` 依 stage 分流）可省一半 run，但 A、C 同模型。**建議**：Phase 0 先測能否指定模型；Phase 2 的 3 輪用兩個 routine 量 run 數，若逼近每日上限就改一個 routine。
舊文件（`專案交接總覽_20261025.md`）寫 A=Gemini、B/C=Sonnet，**以本檔為準**。

---

## 3. 核心原則【確認】

1. **單一寫入者**：`state.json`、`jobs.md`、`master/`、`used_emoji.txt`、`attempts/`、`metrics/`、`reports/check/` 只由總管寫。AI 只交付**兩樣東西**：輸出檔＋回報檔，以 PR 交付。
2. **總管驗證後才寫紀錄**；AI 的 GATE 行只是自述。
3. **AI 只看 `main` 分支的 `state.json` 決定該不該動**：`round`、`stage`＝自己、`status=waiting`，三者同時成立才動作；否則停手回報「無待辦」。`jobs.md` 純給人看。
4. **時間戳由 Actions 蓋章**，ISO 8601 `+08:00`；Actions 跑 UTC，腳本內轉換。AI 回報的時間只當參考。
5. **失敗的 PR 不合併**：總管在 PR 分支上驗證，PASS 才合併進 `main`；FAIL 則把 PR 的檔案與檢查報告**先複製**進 `attempts/N####-X-try#/`，**再**關閉 PR（Claude／Codex 可能在關閉時自動刪分支，順序不可顛倒）。因此 `main` 上的固定路徑在通過前必為空。**所有交付一律走 PR，包括人工修檔**，沒有「直接 push 到 main」的路徑。
6. **重作不得盲做**：`attempt>1` 時 AI 必讀 `state.last_failure_report`（§8.5）。
7. **人工不直接手改 `state.json`／`jobs.md`**，一律透過人工動作（`workflow_dispatch`）讓總管改；Actions 本身壞掉時才依 §7 schema 手改，並在 `jobs.md` 補一行 `人工動作｜手改 state`。
8. **AI 一律從最新 `main` 分出分支**（讀到最新 `state.json`、`used_emoji.txt`）。
9. 輪次、階段、時間一律明確寫出，不用相對說法。

---

## 4. 交接協定（總管 ↔ A／B／C）

### 4.1 時序

```
總管 (Actions)                      main                              AI（A／B／C）
  │ 1 寫 state.json {round, stage, status=waiting, attempt, last_failure_report}
  │ 2 寫 jobs.md「下一步 N0001-A 繼續｜輸入：…」
  │ 3 喚醒（API trigger／@codex／或等排程）────────────────────────────▶ 醒來
  │                                                                     │ 4 讀 main 的 CLAUDE.md 或 AGENTS.md
  │                                                                     │ 5 讀 main 的 state.json
  │                                                                     │   對不上 → 回報「無待辦」，結束
  │                                                                     │   對上 → 讀 prompts/prompt_X.md
  │                                                                     │ 6 由 round 推出輸入／輸出檔名（§4.2）
  │                                                                     │ 7 attempt>1 → 讀 last_failure_report
  │                                                                     │ 8 產出 out_X + reports/N####_X_done.md
  │◀────────────────────────── 9 開 PR 到 main ─────────────────────────│
  │10 pull_request 觸發：驗身分、路徑、ROUND／STAGE（§9.1）
  │11 驗內容：腳本＋diff（§9.2）
  │12a PASS → 合併 → state 推進到下一階段 → jobs「N0001-A 正確」「下一步 N0001-B 繼續」
  │         → repository_dispatch → 回到 1，喚醒下一個 AI
  │12b FAIL → 不合併、複製進 attempts/、關 PR、attempt+1、寫 last_failure_report
  │         → jobs「N0001-A 錯誤」「下一步 N0001-A 重作」→ 回到 1，喚醒同一個 AI
  │12c attempt 達 3，或本次錯誤簽章與上次相同 → status=needs_human、開 Issue、停
```

AI **不需要知道**：嘗試編號、是否有人工介入、上一輪發生什麼。它只需要 `state.json` 的三個欄位加 `last_failure_report`。人工介入後「這一輪改好了」的訊號，對 AI 來說就是 `state.json` 推進到下一個 stage，和自動流程完全相同。

### 4.2 每階段讀什麼、寫什麼（檔名全由 `round` 推出）

| 階段 | 必讀 | 選讀 | 寫（只能動這些） |
|---|---|---|---|
| A | `state.json`、`prompts/prompt_A.md`、`vocab/vocab_####.json`、`used_emoji.txt` | `last_failure_report` | `out_A/N####A_vocab_####.json`、`reports/N####_A_done.md` |
| B | `state.json`、`prompts/prompt_B.md`、`out_A/N####A_vocab_####.json`、`used_emoji.txt` | `reports/check/N####_A.md`（A 的 WARN 清單，幫 B 聚焦）、`last_failure_report` | `out_B/N####B_vocab_####.json`、`reports/N####_B_done.md` |
| C | `state.json`、`prompts/prompt_C.md`、`out_A/…`、`out_B/…` | `reports/check/N####_A.md`、`last_failure_report` | `out_C/N####C_vocab_####.json`、`reports/N####_C_done.md` |

總管識別一個 PR 屬於哪一輪哪一階段，**看回報檔的 `ROUND`／`STAGE` 與改動路徑**，不看分支名（Codex 的分支名不可控）。

### 4.3 AI 無法完成時
AI 不能靜靜失敗等逾時。輸出被截斷、無法產出完整檔、或自己判定 GATE FAIL 時，**仍要開 PR**，回報檔寫 `GATE-X: FAIL｜原因`，輸出檔可缺。總管視為內容錯誤，立即重派（不等 `deadline_at`）。

---

## 5. 檔案格式與命名（#### ＝輪次，4 位數，從 0001）

### 5.1 檔名
| 檔案 | 寫入者 | 意義 |
|---|---|---|
| `vocab/vocab_####.json` | 總管（Phase 1 一次產生） | 第 #### 輪待生成單字 |
| `out_A/N####A_vocab_####.json` | A | A 生成（JSON 陣列） |
| `out_B/N####B_vocab_####.json` | B | 問題清單 `{batch, checked, reviewed[], gate{}, issues[]}` |
| `out_C/N####C_vocab_####.json` | C | C 最終（JSON 陣列） |
| `reports/N####_A|B|C_done.md` | A／B／C | 回報檔（§5.3） |
| `reports/check/N####_A.md`、`N####_C.md` | 總管 | 腳本與 diff 的檢查報告 |
| `attempts/N####-X-try#/` | 總管 | 失敗嘗試的檔案與報告複本 |
| `attempts/N####-rollback-時間戳/` | 總管 | 人工退回上游時清出的下游檔案 |
| `master/N####C_vocab_####.json` | 總管 | 通過的最終檔複本 |
| `master/batch_##_N####-N####.json` | 總管 | 每 10 輪合成的批檔（§14） |
| `master/IMPORTED.md` | 總管（人工動作觸發） | 已匯入 Lovable 紀錄 |
| `master/fixes/` | 人工 | 已通過輪次的事後修正（欄位覆蓋檔），不進流程（§8.3.2） |
| `used_emoji.txt` | 總管 | 每行 `emoji(word)`，初始值來自 `history/` |
| `history/` | Claude Code（Phase 1） | 前 4 批最終檔＋資料庫快照，供 `--history` |
| `metrics/rounds.csv` | 總管 | 每輪耗時、attempt、人工動作次數 |
| `metrics/usage.md` | 人工／Claude Code | 用量紀錄（§13） |

### 5.2 `vocab_####.json`【確認】
```json
{"round":"0001","batch":5,"seq_from":1996,"seq_to":2045,"count":50,
 "words":[{"seq":1996,"word":"switch"},{"seq":1997,"word":"..."}]}
```
`count` 由檔案決定，**N0118 為 31**；所有腳本與 prompt 以 `count` 為準。

### 5.3 回報檔 `reports/N####_X_done.md`【確認，v2.4 補結構化區塊】
前段固定欄位（`KEY: value`，程式解析），中段**結構化 JSON 區塊**（C 必填，A/B 可空），後段自由文字 ≤15 行：
```
ROUND: N0001
STAGE: C
OUTPUT: out_C/N0001C_vocab_0001.json
GATE-C: PASS｜筆數 50/50｜套用 12｜跳過 3｜null 2/2
MODEL: claude-opus-5-5 / low（AI 自述，不知道填 unknown；只供記錄，總管不以此判定）
REPORTED_AT: 2026-10-31T22:41:00+08:00
---
```json
{"a_count":50,"c_count":50,
 "applied":[{"word":"switch","path":"senses[0].examples[1].en"}],
 "skipped":[{"word":"lamp","path":"emoji","reason":"uncertain"}],
 "extra_changes":[{"word":"switch","path":"senses[0].examples[1].zh","reason":"英文例句改動，中文同步"}],
 "nulls":[{"word":"tube","path":"emoji"}]}
```
---
（自由文字）
```
- `applied`／`skipped`／`extra_changes` 是 diff 比對（§9.3）的依據；寫成自由文字會無法程式解析，直接判內容錯誤。
- 解析要**寬鬆**：KEY 大小寫不拘、前後空白忽略、全形冒號視同半形、JSON 區塊有無 ```json 圍欄皆可。Codex 與 Claude 對格式的服從度不同，太嚴會把格式小差異變成內容錯誤、燒掉 attempt。
- GATE 行格式（v3 Gating 逐字）：A `GATE-A: PASS｜筆數 N/N｜順序一致｜emoji null N 個`；B `GATE-B: PASS｜issues N｜reviewed N/N`；C 如上；FAIL 一律 `GATE-X: FAIL｜原因`。

### 5.4 輪次對照【已驗證】
第 k 輪＝序號 1996+50(k−1) 起：N0001＝#1996–2045；N0010＝#2446–2495；N0011＝#2496–2545；N0110＝#7446–7495；N0111＝#7496–7545；N0117＝#7796–7845；**N0118＝#7846–7876，31 字**。第 5–15 批＝每批 10 輪；第 16 批 381 字＝N0111–N0118。

---

## 6. `jobs.md` 格式【確認】

一行一事件，只增不改，只由總管寫，純供人閱讀：
```
[時間] N#### | 階段 | 來源 | 事件 | 內容
```
- 階段：`切檔`、`A`、`B`、`C`、`整輪`
- 來源：`總管`、`A`、`B`、`C`、`人工`
- 事件：`完成`、`驗證通過`、`驗證失敗`、`過期交付`、`拒絕`、`停滯`、`人工動作`、`人工修檔`，及 keyword

Keyword（只由總管寫）：
| 事件 | 格式 |
|---|---|
| 階段結果 | `N0001-A 正確`／`N0001-A 錯誤` |
| 整輪結果 | `N0001 整輪正確`／`N0001 整輪錯誤`／`N0001 跳過` |
| 下一步（兼派工紀錄） | `下一步 N0001-B 繼續`／`下一步 N0001-A 重作` |
| 其他 | `N0001 需人工處理`、`整體暫停`、`全部完成` |

範例：
```
[2026-10-31 22:41:12+08:00] N0001 | A | A | 完成 | PR #12（自述 GATE-A PASS）
[2026-10-31 22:41:50+08:00] N0001 | A | 總管 | 驗證通過 | 50/50、順序一致、check 0 ERROR
[2026-10-31 22:41:51+08:00] N0001 | A | 總管 | N0001-A 正確 |
[2026-10-31 22:41:51+08:00] N0001 | B | 總管 | 下一步 N0001-B 繼續 | 輸入 out_A/N0001A_vocab_0001.json
```

---

## 7. `state.json`【確認】（機器讀的唯一事實來源）

| 欄位 | 用途 |
|---|---|
| `schema_version` | 格式版本 |
| `round`／`total_rounds` | 目前輪次 `"0001"`／118 |
| `stage` | `A`／`B`／`C`／`done`（**沒有 D**；D 在 C 的驗證內） |
| `status` | `waiting`（等 AI）、`validating`、`needs_human`、`paused`、`done` |
| `attempt` | 本階段第幾次嘗試，從 1 起算；上限 3 |
| `last_failure_report` | 上次失敗的檢查報告路徑；無則 null；`attempt>1` 時 AI 必讀 |
| `last_error_signature` | 上次失敗的錯誤簽章（§8.2），用來偵測「同樣的錯再犯」 |
| `stage_started_at`／`deadline_at` | 派工時間／逾時時間（時限 Phase 2 量測後定，暫定每階段 3 小時） |
| `last_ok_round` | 最後一次整輪通過的輪次 |
| `skipped_rounds` | 人工跳過的輪次清單 |
| `consecutive_human_rounds` | 連續需人工處理的輪數；任一輪整輪通過且無人工動作即歸零；達 2 → `paused` |
| `output_sha256` | 各階段通過檔的雜湊 |
| `open_issue` | 目前開啟中的人工處理 Issue 編號，無則 null |
| `updated_at` | 最後更新時間 |

總管更新 `state.json` 與合併 PR 在**同一個 workflow run**內完成，先合併再更新 state；state 更新失敗則整個 run 失敗並開 Issue，避免「已合併但 state 沒推進」。

---

## 8. 錯誤處理與人工接續【確認】

### 8.1 錯誤分類
| 類型 | 例子 | 處置 | 計 attempt |
|---|---|---|---|
| 內容錯誤 | 驗證失敗、腳本 ERROR、diff 不符、回報檔缺或格式錯、AI 自報 GATE FAIL | 不合併、複製進 `attempts/`、關 PR、`attempt+1`、寫 `last_failure_report`、立即重派 | 是 |
| 過期／重複交付 | ROUND／STAGE 與 state 不符、該階段已正確 | 關 PR、留言、記 `過期交付` | 否 |
| 不合規交付 | 作者不在白名單、改到允許路徑外 | 關 PR、記 `拒絕` | 否 |
| 基礎設施 | 額度、網路、排程沒觸發 | 超過 `deadline_at` 記 `停滯`、開 Issue | 否 |

### 8.2 不會無限迴圈的三道保險
1. `attempt` 上限 3。
2. **錯誤簽章比對**：總管把本次失敗的 ERROR 項目正規化成簽章（例如「check_extra:emoji13:lamp」「diff:unexpected:switch.senses[0].zh」的排序集合）。若與 `last_error_signature` **相同**，表示 AI 沒修，直接轉 `needs_human`，不浪費第 3 次。
3. diff 比對採**語意層**（§9.3）而非文字 diff，避免因格式差異永遠比不過。

### 8.3 人工接續：四種動作（`workflow_dispatch`，輸入：輪次、階段、動作、備註）
| 動作 | 總管做什麼 | 何時用 |
|---|---|---|
| 繼續 | 同階段重派，`attempt` 不變，`status=waiting`，喚醒 | 基礎設施問題排除後；解除 `paused` |
| 重作 A／B／C | `attempt=1`、`last_failure_report`／`last_error_signature` 清空、**清除該輪下游檔案**進 `attempts/N####-rollback-…/`、退回該階段、喚醒 | 想讓 AI 重新來過 |
| 人工修檔後驗證 | **使用者本人開 PR**（不是 workflow_dispatch），內含修好的 `out_X` 與回報檔。只在 `status=needs_human` 或 `paused` 時有效，否則視為不合規。總管跑與該階段相同的驗證（§9.2），**diff 預設照跑**；PR 加標籤 `skip-diff` 才略過 diff。PASS → 記 `人工修檔｜diff 執行/跳過`、該階段正確、推進；FAIL → 複製進 `attempts/`、關 PR、維持 `needs_human`，不計 attempt | 見 §8.3.1 |
| 跳過本輪 | 記 `N#### 跳過`、加入 `skipped_rounds`、推進到下一輪 | 使用者明確決定；可之後用「重作」回頭補 |

每個動作記一行 `人工動作`，並關閉 Issue。人工動作之後，下一個 AI 看到的只是 `state.json` 推進，與自動流程無異。

#### 8.3.1 人工修檔時 diff 跑不跑【確認：v2.5 新定】
人工修檔實務上常是「人叫另一個 AI（例如 Claude Code 對話）修出來」，風險與 C 相同（偷改、截斷），所以：
- **AI 代修 → 一定跑 diff**。叫 AI 修時，要求它一併產出回報檔的結構化區塊（`applied`／`extra_changes` 列出它改了哪些 path），diff 自然會過。
- **人親手改幾個欄位 → 可加 `skip-diff`**，仍跑 check_batch／check_extra。`jobs.md` 會記下 `diff 跳過`，可稽核。
- 判斷原則：誰改的不重要，**是不是能列出改了哪些 path** 才重要。列得出來就跑 diff。

#### 8.3.2 流程只處理「目前這一輪」
`state.json` 只有一個 `round`。已整輪正確（甚至已匯入）的輪次，事後發現問題**不回頭重跑 A→B→C**：用 Lovable 既有的「欄位覆蓋」匯入去修（專案交接總覽 §5 已有此機制），並把修正檔放 `master/fixes/`。要整輪重做時，由人工把該輪加回待辦（人工動作「重作」只接受 `round` 等於目前輪，或在 `skipped_rounds` 內的輪）。
【未驗證】手機 GitHub app 能否觸發 `workflow_dispatch`；網頁版可。

### 8.4 煞車
`consecutive_human_rounds` 達 2 → `status=paused`、寫 `整體暫停`、開 Issue。多半是 prompt 或腳本的系統性問題。只能由人工動作「繼續」解除。

### 8.5 重作時的資訊傳遞與下游清除【確認】
- 總管每次判內容錯誤，把檢查報告寫到 `attempts/N####-X-try#/check_report.md`，路徑填入 `last_failure_report`。報告分 **必修（ERROR／diff 不符）** 與 **參考（WARN）** 兩段。
- prompt、`CLAUDE.md`、`AGENTS.md` 都加：「若 `attempt>1`，先讀 `last_failure_report`，修正『必修』段列出的問題；未被指出的內容維持原做法，不要整份重寫。」
- **C 可以修 D 抓到的錯**：D 在 C 階段抓到的 ERROR（如 A 的 emoji 是 Emoji 13、B 沒報），C 重作時可直接修正並列入 `extra_changes`，diff 比對會放行。不過大多數這類錯會在 A 階段就被攔下（§9.2）。
- 退回上游階段時，下游檔案一律清進 `attempts/`，否則 diff 會比到舊版本。

### 8.6 通知：GitHub Issue【確認】
`需人工處理`、`停滯`、`整體暫停` 時開 Issue：標題如 `[需人工處理] N0001-C attempt 2 錯誤簽章重複`；內文含 state 摘要、`last_failure_report` 連結、可用的人工動作與觸發方式；標籤 `needs-human`；同一時間最多一個（`state.open_issue`）；人工動作後由總管關閉。GitHub app 推播是人收到通知的主要途徑。

---

## 9. 交付驗證規則（總管對每個 PR 做）【確認】

### 9.1 身分與範圍（不過就關 PR，不計 attempt）
- 作者白名單：Claude 的 GitHub App、Codex 的 GitHub App（實際顯示身分 Phase 0 測）；**使用者本人的 PR 只在 `status=needs_human`／`paused` 時接受**，視為人工修檔（§8.3.1），其他時候拒絕，避免人誤開 PR 被當成某階段的交付。
- 允許路徑：該階段的輸出檔與回報檔（§4.2）；**動到其他任何檔案一律拒絕**。
- 回報檔 `ROUND`／`STAGE`＝`state.round`／`state.stage`，且 `status=waiting`。

### 9.2 內容（不過算內容錯誤）
| 階段 | 檢查 |
|---|---|
| A | 回報檔可解析；JSON 可解析；筆數＝`vocab.count`；順序與 `vocab.words` 一致；`check_batch.py` 0 ERROR；**`check_extra.py --history history/ master/` 0 ERROR**（Emoji 13+、不被辨識的 emoji 在 A 就攔，讓 A 自己修，不留給 C）。WARN 寫進 `reports/check/N####_A.md` 供 B 參考。 |
| B | 回報檔可解析；JSON 可解析；`reviewed`＝`checked`＝A 筆數；每筆 issue 的 `word`、`path` 在 A 中存在；`severity`、`type` 在允許值內；`fix` 型態合法（topics 為陣列等，照 `apply_b.py` 規則）。 |
| C（含 D） | 回報檔可解析且含結構化區塊；JSON 可解析；筆數與順序＝A；`check_batch.py` 0 ERROR；`check_extra.py --history` 0 ERROR；**diff 比對**（§9.3）。 |

### 9.3 diff 比對（語意層）
1. 把 A、C 都解析成 JSON，逐 word、逐 path 比較**值**；不比文字、不比鍵順序、不比空白與 unicode 跳脫。
2. 每一個值有差異的 path，必須符合其中之一，否則記 `diff:unexpected:<word>.<path>`：
   (a) 等於 B 某個 `severity≠uncertain` 的 issue path，且該 issue 出現在回報檔 `applied`；
   (b) 是 (a) 中某個 `.en` path 的同位置 `.zh`（英文改了中文同步；回報檔有列 `extra_changes` 更好，沒列也放行）；
   (c) 出現在回報檔 `extra_changes`。
3. 反向檢查：回報檔 `applied` 的每個 path 必須真的有差異，否則記 `diff:claimed_not_applied`。
4. B 中「`fix=null` 且 `severity≠uncertain` 且 path 為 emoji／image_query」的每一筆，C 的值必須為 null，否則記 `diff:null_missing`。
5. `skipped` 的 path 必須無差異。
6. 新增或缺少 word、順序不同 → 直接 FAIL（已在筆數檢查）。
以上不符項目全部列進檢查報告「必修」段，C 重作時逐項處理。因為規則是明確可達成的，不會出現「永遠比不過」。

### 9.4 併發與冪等
- Actions `concurrency` 單一群組鎖住總管流程，不取消進行中的 run。
- 同一階段已 `正確` 後的任何交付都是過期。
- AI 只動 `out_X`／`reports/`，總管只動 `state`／`jobs`／`master` 等，檔案不重疊，不會 merge 衝突；**不要**開「分支必須最新才可合併」的保護規則。
- routine 一小時內觸發兩次，第二次因 `status≠waiting` 不動作。

---

## 10. 腳本

- 依賴：`pip install emoji --break-system-packages`（2.16.0）。【已驗證】`check_batch.py` 的 opencc 匯入**從未使用**，移除。
- 【已驗證】`check_batch.py` 永遠 exit 0 → 改成有 ERROR 則 exit 1；單字清單參數改讀 `vocab_####.json`。
- 【已驗證】`check_extra.py` 有 ERROR 時 exit 1；`--history` 傳 `history/*.json`＋`master/*.json`。
- `apply_b.py`：規則同 prompt_C 第一節；乙方案時成為產生最終檔的工具。
- 新增 `diff_check.py`（§9.3）、`validate_report.py`（§5.3 解析）、`error_signature.py`（§8.2）；名稱可改，實作時定。
- **【待決】C 輸出模式**：（甲）整份最終檔；（乙）C 只輸出結構化決定，由 `apply_b.py` 產生最終檔。有 diff 比對後甲的風險可攔；乙省 token。先用甲跑 Phase 2 第 1 輪再決定。

---

## 11. Prompt 與代理自動讀取檔

### 11.0 三份 prompt 已改好【2026-11-01 完成】
repo 流程版 `prompt_A.md`、`prompt_B.md`、`prompt_C.md` 已產出（Claude Project `交接包/04_Repo版Prompt/`，同時附在對話）。已用程式逐行比對 v3 原稿：規則本文全部逐字相同，只有流程句不同（檔案路徑、GATE 行位置、used_emoji 來源、batch 編號格式、path 寫法補充、回報檔格式）。Claude Code 直接上傳到 `prompts/`，**不要再改規則本文**；若 Phase 0 發現交付機制要調，改 `CLAUDE.md`／`AGENTS.md`，不改 prompt。
模型與思考程度：**prompt 無法設定也無法切換模型**（`/model` 是給人下的指令），只能在回報檔 `MODEL:` 欄位自述，總管記錄供人核對 routine 設定是否正確；實際模型由 routine／Codex 任務設定決定。

### 11.1 三份 prompt 的修改處（已套用，留作核對）
1. 輪次 `####`；命名 N####／vocab_####。
2. 輸入依 §4.2 讀檔，不再貼內容。
3. 輸出寫固定檔名＋回報檔（§5.3，C 必含結構化區塊），以 PR 交付；A、C 推 `claude/N####-X` 分支。
4. 「已用過 emoji」改讀 `used_emoji.txt`。
5. GATE 行放回報檔；無法完成也要開 PR 並寫 FAIL（§4.3）。
6. 開始前讀 `main` 的 `state.json`，三條件符合才動作，否則回報「無待辦」。
7. 不得修改允許路徑外的檔案。
8. 以 `vocab.count` 為筆數。
9. `attempt>1` 先讀 `last_failure_report`，只修「必修」段。
10. 規則本文（27 條規則、19 個 topics、JSON schema、16 種 issue 類型）**逐字保留**；模型名改為本檔角色。
11. **prompt_C 補「格式說明」區塊**【確認】：【已驗證】現行 prompt_C 沒有 schema 全文、沒定義 B 的 issues 格式與 path 寫法。補 (a) 最終檔 JSON 結構＋一筆範例；(b) `issues[]` 欄位與 `path` 寫法（如 `senses[0].examples[1].en`）；(c) 回報檔結構化區塊的格式；(d) 乙方案時 C 的輸出格式。並檢查 prompt_B 是否完整定義輸出格式。

固定規則摘要：pos 限 n. v. adj. adv. prep. conj. pron. det. interj.；senses 1–3；每義項例句恰 3 句且含目標字；topics 1–5、限 19 項，「抽象概念與其他」只能單獨；emoji 單一且 Emoji <13 否則 null；image_query 1–3 字或 null；不可含 `pos_list`。

### 11.2 `CLAUDE.md` 與 `AGENTS.md`【確認】
**三層保險，確保 AI 一定讀到自己的 md**：
1. Claude Code 自動讀 repo 根目錄 `CLAUDE.md`、Codex 自動讀 `AGENTS.md`（兩者皆為官方行為），這是第一層。
2. routine 的 prompt（Claude）與 Codex 任務的 prompt，第一句固定寫：「先讀 repo 根目錄的 `CLAUDE.md`（或 `AGENTS.md`）並依其行事。」不靠自動讀取。
3. `prompts/prompt_A|B|C.md` 開頭加一行：「若你尚未讀過 `CLAUDE.md`／`AGENTS.md`，先讀再繼續。」
**`/model` 不適用於 routine**：模型由 routine 本身的設定決定（第三方教學稱建立 routine 時有模型選擇器，Phase 0 確認），prompt 內不得寫 `/model`。
- `CLAUDE.md`（Claude Code 自動讀）：「從最新 `main` 開始；讀 `state.json`；`stage=A` 且 `status=waiting` → `prompts/prompt_A.md`；`stage=C` → `prompt_C.md`；其他不動作並回報無待辦。`attempt>1` 先讀 `last_failure_report`。分支 `claude/N####-X`，只改 §4.2 允許路徑，開 PR 到 `main`。無法完成也要開 PR 寫 FAIL。」加 §0 規則 1、8。
- `AGENTS.md`（Codex 自動讀）：「你只做 B。從最新 `main` 開始；讀 `state.json`；`stage=B` 且 `status=waiting` 才依 `prompts/prompt_B.md`；只改 `out_B/`、`reports/N####_B_done.md`；開 PR 到 `main`；其他情況回報無待辦。`attempt>1` 先讀 `last_failure_report`。」

---

## 11.3 AI 交付前自檢（建議採用）
A 與 C 在開 PR 前，自己先跑 `python3 scripts/check_batch.py` 與 `check_extra.py`，有 ERROR 就先修再交付。好處：少燒 attempt 與總管 run。前提：AI 的雲端環境要有 Python 3 與 `emoji` 套件（§11.4）。若環境裝不起來，就不自檢，交給總管驗證，流程不變。B 不需要（B 輸出的是問題清單）。

## 11.4 環境與工具確認清單（Phase 0 一開始就做）
| 環境 | 要確認 | 用途 |
|---|---|---|
| Claude routine 雲端 | git 可 clone／push `claude/` 分支並開 PR；Python 3 版本；能否 `pip install emoji`（需網路到 PyPI）；routine 的「環境」設定是否有 setup script 與網路開關（第三方教學稱有，未驗證） | A、C 交付與自檢 |
| Codex 雲端 | 能 clone 並開 PR；環境 setup script 與網路設定（未驗證）；思考檔位在排程／任務中如何指定 | B 交付 |
| GitHub Actions runner（總管） | `ubuntu-latest` 內建 Python 3；workflow 內 `pip install emoji`；`gh` CLI 內建 | 所有驗證與記錄 |
| 使用者手機 | GitHub app 能否看到 Issue 推播、能否觸發 `workflow_dispatch`、能否對 PR 加標籤 | 人工接續 |
AI 不需要 opencc（已移除）、不需要 Lovable／Supabase 任何存取。

## 11.5 GitHub 端需要使用者親手設定的項目（Claude Code 無法代做的 repo 設定）
總管＝GitHub Actions，workflow 檔由 Claude Code 寫進 `.github/workflows/`，但下列是 repo 設定頁的事，Phase 1 時由 Claude Code 列出逐步清單，使用者在網頁操作：
1. Settings → Actions → General → Workflow permissions：選 **Read and write permissions**（總管要能推 `state.json`、合併 PR、開 Issue）。「Allow GitHub Actions to create and approve pull requests」視實作需要再開。
2. Settings → Secrets and variables → Actions：**只有**在 Phase 0 確認要用 Claude API trigger 喚醒時，才新增該 token；其他情況不放任何 secret。
3. Issues 的標籤：建立 `needs-human`、`skip-diff`。
4. 分支保護：**不要**開「分支必須最新才可合併」；可以不設任何保護，由總管的驗證負責。
5. 確認 Claude 的 GitHub App 與 Codex 的 GitHub 連線都已授權此 repo（Phase 0 測 PR 時會知道）。
6. Settings → Actions → General：確認 Actions 已啟用（Public repo 預設啟用，Actions 分鐘數對 Public repo 免費）。

## 12. 通訊、觸發與排程

【使用者確認】Claude Code（雲端，已裝 GitHub 整合）與 Codex Cloud 都能對同一 repo 更新同一檔案。
【已驗證，GitHub 官方】`GITHUB_TOKEN` 觸發的事件不會建立新 workflow run；例外 `workflow_dispatch`、`repository_dispatch` 一定會。→ 總管步驟間用 `repository_dispatch` 串接，不用 PAT。AI 的 PR 由 AI 的 App 開，正常觸發 `pull_request`。
【已查】Claude routines：雲端、最短 1 小時、可 clone、有 API trigger（token 需放 Actions secret，是唯一可能需要的 secret）、GitHub 事件觸發需 Claude GitHub App、消耗訂閱額度、有每日 run 上限（數字來自第三方）。ChatGPT Plus：排程任務最多 5 個、最短 1 小時、無 webhook；一般聊天 GitHub 連接器唯讀。

【未驗證，Phase 0 必測】
1. Actions 以 API trigger 喚醒 Claude routine；不行則純排程輪詢。
2. 喚醒 Codex 的方式；Codex 能否排程輪詢；排程時的思考檔位設定。
3. routine 能否分別指定模型（§2）。
4. 手機 GitHub app 能否觸發 `workflow_dispatch`。
5. 兩個 AI 的 App 開 PR 時的作者身分（白名單用）。

速度：354 次交接；全靠 1 小時輪詢約 1–2 週以上；主動喚醒可大幅縮短。每日 run 上限是放大的硬限制，Phase 2 量。

---

## 13. 分階段計畫與放大標準【確認】

**Phase 0 通訊測試**：先過 §11.4 環境清單；再用 `test/ping.md` 測 §12 五項＋`repository_dispatch` 串接。
**Phase 1 骨架**：118 份 `vocab/`、三份 prompt、`scripts/`（exit code、讀 vocab、移除 opencc、新增三支）、`CLAUDE.md`、`AGENTS.md`、`history/`、`used_emoji.txt`、`state.json`、`jobs.md`、最小 workflow。
**Phase 2 試跑**：1 輪 → 3 輪。
**Phase 3 放大**：10 → 20 → 100+。

| 階段 | 過關標準 |
|---|---|
| 1 輪 | 無內容人工介入（手動喚醒可接受，須記錄）、C 驗證 0 ERROR、檔名與 `jobs.md` 合規 |
| 3 輪 | 連續 3 輪無人工介入；`metrics/rounds.csv` 有耗時、attempt；`metrics/usage.md` 有用量；記下單日最大 run 數 |
| 10 輪 | 人工介入率、重試率不上升；推估 118 輪用量 ≤ 月額度 70%；單日 run 未碰上限 |
| 20 輪 | 同上 |
| 100+ | 前面全過才放開 |

量測：`metrics/rounds.csv` 總管自動寫；`metrics/usage.md` 由使用者在 1、3、10 輪後從 Claude／ChatGPT 用量頁抄數字，Claude Code 換算每輪與 118 輪推估。放大前先報推估並確認。每個 Phase 開始前取得「動手開始寫」。

---

## 14. 匯入 Lovable 的銜接【確認】

- 一個批的 10 輪**全部**整輪正確（無 `skipped`）後，總管合成 `master/batch_05_N0001-N0010.json`（500 字）；第 16 批 `batch_16_N0111-N0118.json`（381 字）。有跳過輪的批，等補完才合成。
- 使用者在後台用「只新增」匯入批檔；匯入後用人工動作「標記已匯入」（輸入批號），總管寫 `master/IMPORTED.md`。
- Lovable 預覽會擋格式錯誤，語意問題擋不到；通過 C 驗證者視為可匯入。

---

## 15. 上傳到 GitHub 的內容總表

| 類別 | 路徑 | 寫入者 |
|---|---|---|
| 固定 | `prompts/`、`CLAUDE.md`、`AGENTS.md`、`scripts/`、`vocab/`、`.github/workflows/`、`README.md`、`HANDOFF.md` | Claude Code（Phase 1） |
| 起始資料 | `history/`、`used_emoji.txt` 初始值 | Claude Code（Phase 1） |
| 會變動 | `jobs.md`、`state.json`、`master/`、`used_emoji.txt`、`attempts/`、`metrics/rounds.csv`、`reports/check/` | 僅總管 |
| 會變動 | `out_A|B|C/`、`reports/N####_X_done.md` | 各 AI（經 PR）；人工修檔時人也可 |
| 會變動 | `metrics/usage.md`、`master/IMPORTED.md` | 人工／人工動作 |

---

## 16. 待決與後續

1. C 輸出模式（§10）：Phase 2 第 1 輪後決定。
2. `deadline_at` 時限：Phase 2 量測後定。
3. 一個或兩個 Claude routine（§2）：Phase 2 量 run 數後定。
4. ~~B 的 Thinking 改「中」~~ 【確認】使用者會改。
5. 另案：emoji null 約 1,189 字、標籤補齊、德語版、片語／句型／名言／字首字根。

---

## 17. 參考文件（Claude Project「Lovable-MyFirstWord」內）

- `claude/專案交接總覽_20261025.md`、`claude/單字生成總進度表_20261025.md`
- `交接包/01_Prompt/*`（含 `00_流程與Gating_使用建議.md` 的 GATE 格式）、`交接包/02_檢查腳本/*`、`交接包/03_JSON/*`
- GitHub 官方：About the GITHUB_TOKEN
