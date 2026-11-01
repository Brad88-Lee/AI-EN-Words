# prompt_C.md：C 驗證並套用（repo 流程版，v4.1-repo，2026-11-01）

> v4.1：依 Phase 0 實測加入 AGENT／ATTEMPT 簽名欄位、網路失敗重試、`python3 -m pip` 自檢說明；第一節～第三節規則本文未改。C 輸出模式仍為甲（整份最終檔），是否改乙待使用者決定。
> 由 v3 C prompt 改寫。只改「流程句」（輸入來源、輸出位置、回報方式）；第一節 8 條驗證規則、第二節自掃、第三節輸出規則逐字保留。新增文末「格式說明」（最終檔結構、B 的 issues 結構、path 寫法、回報檔結構化區塊、總管會做的 diff 比對），屬格式補充，不是新規則。交付機制以 `CLAUDE.md` 為準。

---

**若你尚未讀過 repo 根目錄的 `CLAUDE.md`，先讀它再繼續。**

## 任務來源與交付（repo 流程）

1. 先讀 `main` 分支最新的 `state.json`。只有同時符合 `stage` 為 `C`、`status` 為 `waiting` 時才動作；否則回報「無待辦」並結束，不要產出任何檔案。`round` 的四位數就是本輪的 `####`。
2. 若 `attempt` 大於 1，先讀 `last_failure_report` 指向的檢查報告。報告「必修」段列出的每一項都要處理；其中總管程式檢查（check_batch、check_extra、diff 比對）抓到、但不在 B 的 issues 裡的錯，你可以直接修正，並列入回報檔的 `extra_changes`。未被指出的內容維持原做法，不要整份重寫。
3. 輸入：
   - `out_A/N####A_vocab_####.json`：單字資料原稿（JSON 陣列，每字一筆）。
   - `out_B/N####B_vocab_####.json`：審查報告，裡面的 issues 是對原稿的修正「建議」。
   - 選讀 `reports/check/N####_A.md`：總管對 A 的程式檢查 WARN 清單。
4. 輸出兩個檔案：
   - `out_C/N####C_vocab_####.json`：完整的最終單字資料檔。
   - `reports/N####_C_done.md`：回報檔，**必須含結構化 JSON 區塊**（格式見文末）。總管用它做 diff 比對，缺了或寫成自由文字會直接判失敗。回報檔必須含 `AGENT:` 與 `ATTEMPT:` 兩個欄位（`ATTEMPT` 抄 `state.json` 的 `attempt`）。缺欄位、`AGENT` 不合法、或 `ATTEMPT` 與 `state.json` 不符，總管視為不合規／過期交付。
5. 只能新增或修改上述兩個檔案；不得修改 `state.json`、`jobs.md` 或任何其他檔案。
6. 若無法完成（輸出被截斷、筆數對不上），**仍要交付回報檔**，GATE-C 寫 `FAIL｜原因`，不要宣稱可匯入。
7. 建議自檢（環境有 Python 3 與 `emoji` 套件時）：交付前先跑 `python3 scripts/check_batch.py out_C/N####C_vocab_####.json vocab/vocab_####.json` 與 `python3 scripts/check_extra.py out_C/N####C_vocab_####.json --history history/*.json master/*.json`，有 ERROR 先修並列入 `extra_changes`。環境沒有 Python 就略過；沒有 `emoji` 套件時先執行 `python3 -m pip install emoji`（一律用 `python3 -m pip`，不要直接打 `pip`）。
8. 交付方式（分支、開 PR）依 `CLAUDE.md`；`git push` 或開 PR 遇到網路錯誤（例如 proxy、connection）時，等待約 30 秒後重試，最多 3 次，每次嘗試都記在回報檔自由文字；仍失敗才在回報檔寫 `GATE-X: FAIL｜原因`。PR 已存在（already exists）視為成功，不要當錯誤。

---

你是資料驗證與套用員。有兩個檔案：
- `out_A/N####A_vocab_####.json`：單字資料原稿（JSON 陣列，每字一筆）。
- `out_B/N####B_vocab_####.json`：審查報告，裡面的 issues 是對原稿的修正「建議」。

你的任務：逐筆驗證每個建議是否正確，只套用「有把握正確」的建議，產出完整的最終單字資料檔 `out_C/N####C_vocab_####.json`。

## 一、逐筆驗證每個 issue（每一筆都要做）

對 B 的每一筆 issue，先做這些檢查，全部通過才套用：
1. word 與 path 在 A 中真實存在，且 fix 是針對「這個欄位」寫的（不是別句、別字的內容）。
2. severity 為 uncertain：不套用，列入「跳過」。fix 為 null 時要分兩種：(a) path 是 emoji 或 image_query，且 severity 不是 uncertain，代表「要把該欄位清空」，**必須套用，把欄位設為 null**（這是修正，不是跳過）；(b) 其他 path 的 fix 為 null：不套用，列入「跳過」。
3. 套用後欄位型態仍正確：例句為字串；topics 為陣列（1～5 個，只能是下列 19 項，「抽象概念與其他」只能單獨使用）；emoji 為單一 emoji 或 null；image_query 為 1～3 個英文單字或 null。
4. 英文例句修正後必須包含該單字本身（變化形可、複合字不可），語法完整，不加贅字（today、every single 等），長度約 8～18 字。
5. 中文必須是台灣繁體與台灣慣用語，忠實對應英文（人稱、單複數、時態一致，不增譯、不漏譯）。若英文例句被改，對應中文必須同步（B 沒另外回報時，請你自己改中文使其與新英文一致，並列入「額外修改」）。
6. 義項中文（zh）的詞性必須與 pos 一致，並涵蓋該義項 3 個例句用到的意思。
7. 若兩筆 issue 修改同一欄位，以較合理者為準，另一筆列入跳過。
8. 套用後內容不得比原稿更差、更怪，或引入新的暴力、色情、政治爭議、品牌內容。

topics 清單（19 項）：日常生活、飲食、家庭與人際、學校與學習、工作與商業、金融與會計、健康與身體、情緒與性格、動物、植物與自然、天氣與環境、科技與網路、交通與旅行、運動與休閒、藝術與文化、社會與法律、科學、歷史與地理、抽象概念與其他。
詞性只允許：n. v. adj. adv. prep. conj. pron. det. interj.。

## 二、你自己也要掃一次（B 可能漏看）

套用完 issue 後，再對每個單字快速檢查：senses 不超過 3 筆、每個義項的 examples 恰好 3 筆；topics 與 image_query 符合規則；沒有簡體字與大陸用語；沒有暴力、血腥、犯罪細節（例如 kill、murder、attack 的負面情境）；每個英文例句都含該單字；emoji 是否對應第一義項、是否太新或易誤解（有疑慮就設為 null）；義項 zh 列出的每個意思是否都有例句用到。發現問題請直接修正，並列入「額外修改」。另外檢查：例句中的目標字是否只靠含連字號的複合詞或合成字（有就改寫該句，並同步中文）；topics 是否超過 3 個（超過就精簡到最相關的）。

## 三、輸出規則（很重要）

- 最終檔案是「完整的 JSON 陣列」，筆數與順序必須與 A 完全一致；每個單字一行、不縮排、`separators` 為最精簡格式；保留 A 的所有欄位與欄位順序（word、senses、topics、emoji、image_query）。
- **只能改上面驗證通過的欄位**；沒有被列入修改的內容必須與 A 逐字相同，不可順手改寫、不可省略、不可截斷。
- 不確定時寧可不改，也不要編造。
- 檔案之外，請在回報檔 `reports/N####_C_done.md` 回報（結構化區塊＋自由文字不超過 15 行）：
  1. A 的筆數、最終檔的筆數（必須相同）。
  2. 已套用的 issue 數、跳過的 issue 數。
  3. 跳過清單：word、path、跳過原因（例如「fix 對應的是別句」「uncertain」）。
  4. 額外修改清單：word、path、原因。
  5. emoji 或 image_query 被設為 null 的字清單（必須與 B 中 fix 為 null 且非 uncertain 的 emoji／image_query issue 一一對應，少一個都要說明原因）。
  6. 最後一行判定：通過時輸出 `GATE-C: PASS｜筆數 N/N｜套用 X｜跳過 Y｜null Z/Z`（Z/Z 表示應設為 null 的數量與實際設為 null 的數量相同）；筆數不同、或 Z 不相等、或輸出被截斷時，輸出 `GATE-C: FAIL｜原因`，並且不要宣稱檔案可匯入。

---

## 格式說明（格式補充，供你精確定位與輸出）

### 1. 最終檔每一筆的結構（與 A 相同）
```
{"word":"小寫單字",
 "senses":[{"pos":"n.","zh":"義項一；義項二","examples":[{"en":"…","zh":"…"},{"en":"…","zh":"…"},{"en":"…","zh":"…"}]}, …最多 3 筆],
 "topics":["主分類", …1～5 個],
 "emoji":"單一 emoji 或 null",
 "image_query":"1～3 個英文字 或 null"}
```
範例（取自已匯入資料的格式，內容勿照抄）：
{"word":"light","senses":[{"pos":"n.","zh":"光；光線；燈","examples":[{"en":"The light in the room was too dim to read by.","zh":"房間裡的光線太暗，沒辦法閱讀。"},{"en":"Please turn off the light before you leave.","zh":"離開前請關燈。"},{"en":"Sunlight is the main source of light on Earth.","zh":"陽光是地球上光線的主要來源。"}]},{"pos":"adj.","zh":"輕的；淺色的；清淡的","examples":[{"en":"This backpack is light enough for a child to carry.","zh":"這個背包很輕，小孩也背得動。"},{"en":"She wore a light blue dress to the party.","zh":"她穿了一件淺藍色洋裝去參加派對。"},{"en":"We had a light lunch because we were not very hungry.","zh":"我們不太餓，所以午餐吃得很清淡。"}]}],"topics":["日常生活","科學"],"emoji":"💡","image_query":"glowing light bulb"}
A 裡若有 `{"word":"…","error":"…"}` 這種筆，原樣保留，不要補內容。

### 2. B 檔（`out_B/…`）的結構
```
{"batch":"N####","checked":數字,"reviewed":["word",…],
 "gate":{"a_count":數字,"checked":數字,"reviewed_count":數字,"pass":true|false,"reason":"…"},
 "issues":[{"word":"…","path":"…","type":"類型代碼","severity":"high|medium|low|uncertain","detail":"…","fix":新值或 null}, …]}
```
`type` 為 16 種代碼之一（pos_wrong、pos_missing、zh_wrong、zh_missing、zh_unclear、example_missing_word、example_unnatural、example_style、example_similar、translation_bad、mainland_term、simplified_char、topics_bad、emoji_bad、image_query_bad、format_bad），只供理解，不影響你的套用判斷。

### 3. path 寫法（索引從 0 起算）
`senses[i].pos`、`senses[i].zh`、`senses[i].examples[j].en`、`senses[i].examples[j].zh`、`topics`、`emoji`、`image_query`。其他形式的 path 視為不存在，列入跳過並寫原因。

### 4. 回報檔 `reports/N####_C_done.md` 的完整格式
```
ROUND: N0001
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0001C_vocab_0001.json
GATE-C: PASS｜筆數 50/50｜套用 12｜跳過 3｜null 2/2
MODEL: （若你知道自己是哪個模型與思考程度就填；不知道填 unknown）
REPORTED_AT: 2026-11-01T12:00:00+08:00
---
```json
{"a_count":50,"c_count":50,
 "applied":[{"word":"switch","path":"senses[0].examples[1].en"}, …],
 "skipped":[{"word":"lamp","path":"emoji","reason":"uncertain"}, …],
 "extra_changes":[{"word":"switch","path":"senses[0].examples[1].zh","reason":"英文例句改動，中文同步"}, …],
 "nulls":[{"word":"tube","path":"emoji"}, …]}
```
---
（自由文字：不超過 15 行；第三節第 1～5 點的摘要）
```
- `applied`：真的套用了的 B issue（word＋path）。
- `skipped`：沒套用的 B issue 與原因。
- `extra_changes`：不在 B issues 內、但你依第二節自掃或失敗報告修改的每一個欄位。**你改過的每一個 path 都必須出現在 `applied` 或 `extra_changes`。**
- `nulls`：依第一節第 2 條 (a) 設為 null 的欄位。

### 5. 總管會對你的輸出做什麼（讓你知道怎樣會過）
1. 把 A 與 C 解析成 JSON，逐 word、逐 path 比較值（不比排版）。
2. 每一個值有差異的 path，必須是：`applied` 中的 path；或 `applied` 中某個 `.en` 的同位置 `.zh`；或 `extra_changes` 中的 path。否則判失敗，列出該 path。
3. `applied` 中的每個 path 必須真的有差異；`skipped` 的 path 必須無差異。
4. B 中「fix 為 null、severity 非 uncertain、path 為 emoji 或 image_query」的每一筆，C 的值必須為 null。
5. 筆數、順序必須與 A 相同；再跑 check_batch 與 check_extra，ERROR 必須為 0。
這些都是明確可達成的條件；照第三節的規則做、把改過的 path 如實列出，就會通過。
