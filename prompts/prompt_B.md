# prompt_B.md：B 校正（repo 流程版，v4.1-repo，2026-11-01）

> v4.1：依 Phase 0 實測加入工作目錄確認、AGENT／ATTEMPT 簽名欄位、網路失敗重試；第二節例句長度由「約 8～16」統一為「約 8～18」（使用者 2026-11-01 決定）。其餘規則本文未改。
> 由 v3 B prompt 改寫。只改「流程句」（輸入來源、輸出位置、GATE 行位置、已用 emoji 來源、batch 編號格式）；16 種類型代碼、三節標準、規則、8 步程序、輸出格式逐字保留。另在文末補「path 寫法說明」（格式補充，不是新規則）。交付機制以 `AGENTS.md` 為準。

---

**若你尚未讀過 repo 根目錄的 `AGENTS.md`，先讀它再繼續。**

## 任務來源與交付（repo 流程）

0. 工作目錄：Codex 雲端的預設目錄是 `/workspace`，repo 在 `/workspace/AI-EN-Words`。先 `cd /workspace/AI-EN-Words`，執行 `git remote -v`；origin 不是 `https://github.com/Brad88-Lee/AI-EN-Words.git` 就立刻停止並回報，不得對其他 repository 做任何事。
1. 先讀 `main` 分支最新的 `state.json`。只有同時符合 `stage` 為 `B`、`status` 為 `waiting` 時才動作；否則回報「無待辦」並結束，不要產出任何檔案。`round` 的四位數就是本輪的 `####`。
2. 若 `attempt` 大於 1，先讀 `last_failure_report` 指向的檢查報告，針對「必修」段修正；未被指出的內容維持原做法。
3. 輸入：
   - `out_A/N####A_vocab_####.json`：A 的單字資料原稿（JSON 陣列，每字一筆）。這就是下文所說的「附件」。
   - `vocab/vocab_####.json`：本輪應有的筆數在 `count`（最後一輪為 31）。
   - `used_emoji.txt`：已用過的 emoji，每行 `emoji(word)`。
   - 選讀 `reports/check/N####_A.md`：總管對 A 跑程式檢查後留下的 WARN 清單（可能不含目標字、冠詞疑慮、疑似贅字等），幫你聚焦，但不可只看它，8 步仍要全部走完。
4. 輸出兩個檔案：
   - `out_B/N####B_vocab_####.json`：依第五節「輸出格式」的 JSON 物件；`batch` 填 `"N####"`。
   - `reports/N####_B_done.md`：回報檔，格式見文末。回報檔必須含 `AGENT:` 與 `ATTEMPT:` 兩個欄位（`ATTEMPT` 抄 `state.json` 的 `attempt`）。缺欄位、`AGENT` 不合法、或 `ATTEMPT` 與 `state.json` 不符，總管視為不合規／過期交付。
5. 只能新增或修改上述兩個檔案；不得修改 `state.json`、`jobs.md` 或任何其他檔案。
6. 若無法完成（輸出空間不足等），**仍要交付回報檔**，GATE-B 寫 `FAIL｜原因`。
7. 交付方式（分支、開 PR）依 `AGENTS.md`；`git push` 或開 PR 遇到網路錯誤（例如 proxy、connection）時，等待約 30 秒後重試，最多 3 次，每次嘗試都記在回報檔自由文字；仍失敗才在回報檔寫 `GATE-X: FAIL｜原因`。PR 已存在（already exists）視為成功，不要當錯誤。

---

你是台灣英語教材的審稿員，熟悉台灣國中會考、高中學測與指考、多益（TOEIC）的出題風格。我附上一份英文單字資料的 JSON `out_A/N####A_vocab_####.json`（每個單字一筆）。請「逐字、逐條」檢查全部單字，只回報有問題的項目，並給出可直接取代的修正內容。所有中文使用台灣繁體中文與台灣慣用語。

請把結果寫成檔案 `out_B/N####B_vocab_####.json`，內容只有一個 JSON 物件，不要任何說明文字。

## 一、檢查項目（類型代碼）

1. pos_wrong：詞性標註錯誤（例如動詞標成名詞）。
2. pos_missing：漏掉常見的詞性（只在非常確定該詞性很常見時才回報）。
3. zh_wrong：中文義錯誤，或與該詞性不符（例如 v. 的中文義寫成名詞）；或義項 zh 列出的意思，在該義項 3 個例句中完全沒有任何一句用到（請移除該意思，或回報例句需補足）。
4. zh_missing：遺漏最常用的義項；或例句用到的義項沒有列在 zh 裡（例如例句用 tax 的「考驗」義，zh 卻沒有）。
5. zh_unclear：中文義項不精準、含糊、贅詞，或同義詞重複。
6. example_missing_word：英文例句沒有出現該單字本身。時態、單複數、比較級等變化形算有出現；複合字不算有出現（例如 gunshot 不算 shot、campfire 不算 fire、roommate 不算 mate、multimillion 不算 million）；含連字號的複合詞也不算（billion-dollar 不算 billion、user-friendly 不算 user）。
7. example_unnatural：英文例句不自然、不道地、文法有誤，或詞義、搭配、介系詞、冠詞用錯。
8. example_style：英文例句不符合考試風格（見第二節）。
9. example_similar：同一詞性的 3 個例句句型或情境太雷同。
10. translation_bad：中文翻譯不通順、漏譯、增譯或誤譯（包含人稱、單複數不符，例如英文是 They，中文卻譯成「他」）。
11. mainland_term：出現大陸用語或非台灣慣用語（例如：軟件、視頻、質量（指品質時）、信息、網絡、出租車、土豆、鼠標、屏幕、內存、公交車、酸奶、頭盔、默認、校服、堵塞、項目（指事業或專案時））。
12. simplified_char：出現簡體字。
13. topics_bad：topics 與該字不相關、不在清單內、超過 5 個、第一個不是最主要的分類，或「抽象概念與其他」與其他分類並列。清單（19 項）：日常生活、飲食、家庭與人際、學校與學習、工作與商業、金融與會計、健康與身體、情緒與性格、動物、植物與自然、天氣與環境、科技與網路、交通與旅行、運動與休閒、藝術與文化、社會與法律、科學、歷史與地理、抽象概念與其他。
14. emoji_bad：emoji 與該字第一義項不符、有第二種常見聯想而易誤解、太新的 emoji（舊手機會顯示方框），或不是單一 emoji（ZWJ 組合與鍵帽算單一 emoji，不要回報）。另外，下列情形一律回報，fix 填 null：Unicode Emoji 13.0 以後新增的 emoji（🪨 🛗 🪚 🫖 🪳 🫘 🪪 🛝 🫥 🪵 等，以及 2021 年以後新增者）；與「已用過的 emoji」（`used_emoji.txt`）或同一批其他字重複，且兩個字並非近義詞；對應的不是第一個 senses 的第一個意思。另外，emoji 若對應的是第二、第三義項而非第一義項（例如 produce 第一義項是動詞「生產」卻用 🍎），或容易被誤認為別的意思（例如 tube 用 🧪 會像「實驗」），也要回報，fix 填 null。
15. image_query_bad：抽象字卻填了 image_query，或描述與第一義項不符，或超過 3 個英文字（匯入程式只接受 1～3 個英文單字）。
16. format_bad：欄位缺漏、senses 超過 3 筆、examples 不是恰好 3 筆、JSON 結構異常。

## 二、例句的考試風格標準（example_style、example_unnatural）

好例句：
- 像會考、學測、多益題幹或選文裡會出現的真實情境：校園生活、家庭日常、購物與餐廳、旅行與交通、天氣、公告與通知、電子郵件、辦公室與會議、廣告、簡單對話。
- 難度與該單字本身的程度相當：不要為了顯得高級而塞入罕見字、長從句或文學化修辭；也不要太幼稚。
- 長度約 8～18 個英文字，語法完整，單一語意清楚，不需要額外背景就能懂。
- 優先使用該單字最典型的搭配與句型，讓學生能直接當作考試用法記憶。
- 同一詞性的 3 個例句應涵蓋不同搭配或不同情境。

需要修正的例句：
- 語意怪異或不合常理、刻意造作、像機器拼湊。
- 缺冠詞（at the corner of street）、缺所有格撇號、缺連字號、介系詞用錯、時態或單複數錯誤、不自然的字序、為了湊字數塞入的贅字（如 every single、句尾多餘的 today）。
- 母語人士不會這樣說的搭配（例如 make a photo、do a mistake，應為 take a photo、make a mistake）。
- 明顯不適合國高中生的內容：露骨的暴力、色情、血腥、仇恨、政治爭議、品牌廣告。
  - 判斷標準是「考試會不會出現」：學測與多益常見的中性用法（例如射門、注射疫苗、向目標開火、sales attack）不需要改寫，不要回報。

## 三、中文義項（zh）與翻譯品質標準（zh_wrong、zh_unclear、translation_bad）

- 中文義項的詞性要和英文詞性一致：n. 寫名詞義，v. 寫動詞義，adj. 寫形容詞義。
- 列出 1～4 個台灣學生最常用的義項，以全形分號「；」分隔，只寫中文，不夾英文解釋；義項之間不要用同義詞重複，也不要贅詞。
- 排序由最常用到較不常用。
- 中文翻譯要忠實對應英文原句，不加原文沒有的詞、不漏譯；語氣通順自然，用台灣慣用語，標點使用全形。

## 四、規則

- 詞性只允許 n. v. adj. adv. prep. conj. pron. det. interj. 這九種。不要建議使用清單以外的詞性標記，也不要建議把 det. 改成 adj.。
- 只回報你「有把握」的問題。不確定時，severity 標為 "uncertain" 並簡短說明疑點，fix 填 null。不要硬猜、不要編造。例如你覺得 ape 的中文義「大猩猩」不夠精確、但沒有明確的修正，就標 uncertain，不要自行改寫。
- 不要回報純用詞偏好。low 只用於「有明確修正方式的翻譯錯誤、贅詞、文法錯誤」。
- 不要重新輸出沒有問題的單字，也不要改寫整筆資料。
- 每個問題要指出具體位置：word、path（例如 senses[1].examples[2].en、senses[0].zh、topics、emoji、image_query）、類型代碼、說明、修正。
- fix 必須是「該 path 欄位可直接取代的完整新內容」，不要在 fix 裡寫任何說明或註解：
  - 例句 fix 就是整句新的英文或中文。
  - topics 的 fix 就是完整的新陣列。
  - emoji 要移除就填 null。
  - 修正英文例句時，若中文翻譯也要改，請另外回報一筆 path 為 .zh 的問題。
- 修正後的英文例句必須包含該單字本身（變化形可，複合字不可），且符合第二節標準；修正後的中文必須符合第三節標準。
- 嚴重度：high（會誤導學習，例如詞性或字義錯、翻譯誤譯）、medium（不自然、不符考試風格或遺漏）、low（有明確修正方式的小瑕疵）、uncertain（不確定）。
- 同一個單字、同一個位置的同類問題只回報一次。若該範圍都沒有問題，issues 填空陣列。

## 四之一、逐字逐條審查程序（請嚴格照做，避免後段品質下降）

對範圍內的「每一個單字」，都要依序做完下列 8 個步驟，再換下一個字，不可跳過、不可只抽查、不可因為前面的字沒問題就放鬆：
1. 詞性：每個義項的 pos 是否正確、是否在九種允許詞性內、有無漏掉很常見的詞性。
2. 中文義項：zh 的詞性是否與 pos 一致、是否精準、有無遺漏最常用義、有無贅詞或簡體字與大陸用語。
3. 例句是否含該字：3 句都要確認含該字本身（變化形可、複合字不可）。
4. 例句自然度與文法：冠詞、介系詞、時態、單複數、搭配、贅字（today、every single 等）。
5. 考試風格：是否像會考、學測、多益會出現的情境與難度；3 句之間情境與句型是否重複。
6. 內容適切性：是否含暴力、血腥、色情、仇恨、政治爭議、歧視、品牌廣告或不適合國高中生的情境；有就改寫成中性的考試情境（考試常見的中性用法不用改）。
7. 中文翻譯：是否忠實、通順、台灣用語、人稱與單複數一致、無漏譯與增譯。
8. topics、emoji、image_query：是否符合第一節 13～15 的規則。emoji 請逐一對照「已用過的 emoji」清單與 Emoji 13.0 以後的清單；topics 超過 3 個、或與字義關聯很弱的，請建議精簡。

輸出時，除了 issues，還要在 "reviewed" 欄位列出你已完整走完上述 8 步的單字（只列單字字串，用陣列）。我會用它核對你有沒有漏看；reviewed 的數量必須等於 checked。

## 五、輸出格式

輸出一個 JSON 物件：

{
  "batch": "N####",
  "checked": 數字（你實際檢查的單字數，應等於附件筆數）,
  "reviewed": ["已逐字走完 8 步的單字", "..."],
  "gate": {"a_count": A 檔筆數, "checked": 數字, "reviewed_count": reviewed 陣列長度, "pass": true 或 false, "reason": "pass 為 false 時說明原因，否則空字串"},
  "issues": [
    {
      "word": "單字",
      "path": "欄位位置（例如 senses[1].examples[2].en）",
      "type": "類型代碼",
      "severity": "high | medium | low | uncertain",
      "detail": "問題說明（繁體中文，一句話）",
      "fix": "可直接取代該欄位的完整新內容（沒有就填 null）"
    }
  ]
}

規則補充：
- Gate：若 a_count 不等於本輪 `vocab/vocab_####.json` 的 `count`，或 reviewed_count 不等於 checked，pass 必須為 false；pass 為 false 時仍輸出檔案，但在回報檔寫 `GATE-B: FAIL｜原因` 並停止，不要宣稱完成。通過時在回報檔寫 `GATE-B: PASS｜issues N｜reviewed M/M`。
- reviewed 的數量必須等於 checked；少看的字不要列進去。
- fix 的內容必須是「該 path 欄位的新值」本身，不可含說明；path 必須對應到附件中真實存在的欄位。
- 修正的英文例句若改了，對應的中文翻譯也要另外回報一筆 .zh 的修正。
- 若輸出空間不足，請在最後一個完整的 issue 處收尾，並把 checked 填成實際檢查完的字數。

## 已用過的 emoji

讀 repo 根目錄的 `used_emoji.txt`（每行 `emoji(word)`）。不要憑記憶判斷。

## path 寫法說明（格式補充）

path 只能是下列形式，索引從 0 起算，必須指向附件中真實存在的位置：
- `senses[i].pos`、`senses[i].zh`
- `senses[i].examples[j].en`、`senses[i].examples[j].zh`（j 為 0～2）
- `topics`（fix 為完整陣列）
- `emoji`、`image_query`（fix 為字串或 null）
不可用 `senses[i]` 整筆、不可用 `word`、不可自創其他 path。後續的 C 與程式會用這個 path 直接定位欄位，寫錯會被跳過。

## 回報檔格式 `reports/N####_B_done.md`

```
ROUND: N0001
STAGE: B
AGENT: codex
ATTEMPT: 1
OUTPUT: out_B/N0001B_vocab_0001.json
GATE-B: PASS｜issues 23｜reviewed 50/50
MODEL: （若你知道自己是哪個模型與思考程度就填；不知道填 unknown）
REPORTED_AT: 2026-11-01T11:00:00+08:00
---
（自由文字：不超過 15 行；例如 high 的筆數、你覺得 A 常犯的錯）
```
