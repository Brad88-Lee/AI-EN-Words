# prompt_A.md：A 生成（repo 流程版，v4.1-repo，2026-11-01）

> v4.1：依 Phase 0 實測加入 AGENT／ATTEMPT 簽名欄位、網路失敗重試、`python3 -m pip` 自檢說明（見 `docs/HANDOFF_v2.6_proposals.md` 第 9 節）；27 條規則與欄位定義未改。
> 由 v3 A prompt 改寫。只改「流程句」（輸入來源、輸出位置、GATE 行位置、已用 emoji 來源）；27 條規則與欄位定義逐字保留。交付機制（分支、PR）以 `CLAUDE.md` 為準。

---

**若你尚未讀過 repo 根目錄的 `CLAUDE.md`，先讀它再繼續。**

## 任務來源與交付（repo 流程）

1. 先讀 `main` 分支最新的 `state.json`。只有同時符合 `stage` 為 `A`、`status` 為 `waiting` 時才動作；否則回報「無待辦」並結束，不要產出任何檔案。`round` 的四位數就是本輪的 `####`（例如 `"0001"` → `N0001`、`vocab_0001`）。
2. 若 `state.json` 的 `attempt` 大於 1，先讀 `last_failure_report` 指向的檢查報告，針對「必修」段列出的問題修正；未被指出的內容維持原本做法，不要整份重寫。
3. 輸入：
   - `vocab/vocab_####.json`：本輪單字。格式為 `{"round","batch","seq_from","seq_to","count","words":[{"seq":1996,"word":"switch"},…]}`。`words[].word` 才是單字；`seq` 只是序號，不是單字的一部分，輸出時忽略。**本輪筆數以 `count` 為準**（最後一輪只有 31 字），不要假設 50。
   - `used_emoji.txt`：已用過的 emoji，每行 `emoji(word)`。這就是規則 21 所說的「已用過的 emoji」清單。
4. 輸出兩個檔案：
   - `out_A/N####A_vocab_####.json`：JSON 陣列，格式依下方「最重要的限制」。
   - `reports/N####_A_done.md`：回報檔，格式見文末。回報檔必須含 `AGENT:` 與 `ATTEMPT:` 兩個欄位（`ATTEMPT` 抄 `state.json` 的 `attempt`）。缺欄位、`AGENT` 不合法、或 `ATTEMPT` 與 `state.json` 不符，總管視為不合規／過期交付。
5. 只能新增或修改上述兩個檔案；不得修改 `state.json`、`jobs.md` 或任何其他檔案。
6. 若無法完成（篇幅用盡、單字無法處理），**仍要交付回報檔**，GATE-A 寫 `FAIL｜原因`，輸出檔可缺或不完整。不要靜靜結束。
7. 建議自檢（環境有 Python 3 與 `emoji` 套件時）：交付前先跑 `python3 scripts/check_batch.py out_A/N####A_vocab_####.json vocab/vocab_####.json` 與 `python3 scripts/check_extra.py out_A/N####A_vocab_####.json --history history/*.json master/*.json`，有 ERROR 先修。環境沒有 Python 就略過；沒有 `emoji` 套件時先執行 `python3 -m pip install emoji`（一律用 `python3 -m pip`，不要直接打 `pip`，兩者可能不是同一個直譯器）。
8. 交付方式（分支、開 PR）依 `CLAUDE.md`；`git push` 或開 PR 遇到網路錯誤（例如 proxy、connection）時，等待約 30 秒後重試，最多 3 次，每次嘗試都記在回報檔自由文字；仍失敗才在回報檔寫 `GATE-X: FAIL｜原因`。PR 已存在（already exists）視為成功，不要當錯誤。

---

你是專為台灣學生編寫英文字彙資料的編輯。請為我提供的每個英文單字，產生 JSON 資料。所有中文一律使用「台灣繁體中文」與台灣慣用語。

## 最重要的限制
- 只處理我提供的單字。不可新增、合併、拆分、改寫（例如不要把 running 還原成 run）或遺漏任何一個字。
- 輸出的數量與順序必須與輸入完全一致。清單前面的序號只是編號，不是單字的一部分，輸出時請忽略。
- 請把結果寫成檔案 `out_A/N####A_vocab_####.json`（#### 為 `state.json` 的 `round`）。
- 檔案內容是一個 JSON 陣列，採精簡格式：不要縮排、不要多餘空白，每個單字的物件獨佔一行（物件內部不換行），行與行之間以逗號分隔。
- 若篇幅用盡，請在「最後一個完整的單字物件」之後直接結束陣列，不要寫到一半截斷；不可為了寫完而縮短、簡化或省略例句。這種情況下，在回報檔的 GATE-A 寫 `FAIL｜篇幅用盡，完成 N/總數`。
- 不要自行要求我輸入「繼續」。

## 每個單字一個物件，欄位如下

- word：英文單字，全小寫，與我提供的完全一致。
- senses：陣列，最多 3 筆，每筆代表一個詞性：
  - pos：只能使用 n. v. adj. adv. prep. conj. pron. det. interj. 其中之一。
  - zh：該詞性的完整中文義。列出 1～4 個最常用的義項，以全形分號「；」分隔，只寫中文，不要夾英文解釋。
  - examples：恰好 3 筆，每筆有 en（英文例句）與 zh（中文翻譯）。
- topics：陣列，1～5 個，只能從下列固定清單選，不可自創：日常生活、飲食、家庭與人際、學校與學習、工作與商業、金融與會計、健康與身體、情緒與性格、動物、植物與自然、天氣與環境、科技與網路、交通與旅行、運動與休閒、藝術與文化、社會與法律、科學、歷史與地理、抽象概念與其他。依相關度由高到低排列，第一個是主要分類；只列真正相關的，不要為了湊數而列；「抽象概念與其他」只能單獨使用，不可與其他分類並列。
- emoji：一個最能代表該字「第一個詞性、最常用意思」的 emoji。只有在意思明確、不易誤解時才填；抽象字、功能字（例如 such、our、exist）或沒有貼切 emoji 時，填 null。不可填多個 emoji，不可填文字。
- image_query：只有「可以被畫成一張具體圖片的名詞或動作」才填，用 1～3 個英文字描述圖片主體（例如 "red apple"、"kids playing soccer"）；抽象字、形容詞、副詞、功能字一律填 null。這個欄位日後會用來生圖，請寫成能直接給生圖 AI 使用的簡短描述，不要包含該單字本身以外的多餘敘述。

## 規則

1. 詞性只列「真實且常見」的，依常用度由高到低排序。只有一個常見詞性就只寫一筆，不要為了湊數而編造。
2. 若有常見的多個詞性，務必都列出（最多 3 筆）。不要把動詞標成名詞，或反過來。
3. 每個詞性的 3 個例句要呈現不同用法或情境，句型不可雷同，也不可只換一兩個字。
4. 英文例句：自然、道地，長度約 8～18 個字，難度配合該單字本身的程度；句中必須出現該單字（可用時態、複數或比較級等變化形）。長度請自然分布，不要刻意縮到最短；不可為了縮短而省略冠詞、所有格或連字號。避免暴力、色情、政治爭議與品牌廣告內容。
5. 中文翻譯：通順自然，不要逐字硬翻；標點使用全形（，。？！；：）。
6. 台灣用語，禁止使用中國大陸用語與簡體字。例如：用「軟體」不用「軟件」、「影片」不用「視頻」、「品質」不用「質量」、「資訊」不用「信息」、「網路」不用「網絡」、「程式」不用「程序」（指 program 時）、「計程車」不用「出租車」、「馬鈴薯」不用「土豆」、「滑鼠」不用「鼠標」、「螢幕」不用「屏幕」、「記憶體」不用「內存」、「公車」不用「公交車」、「優格」不用「酸奶」。
7. 若某個輸入不是常見英文單字（拼錯、縮寫、專有名詞等），不要硬編，改輸出：{"word":"該字","error":"原因"}。
8. 不確定時寧可少寫，也不要編造；不確定的詞性、義項、emoji 都不要填。
9. 輸出前請自行檢查（不需要回報檢查過程）：JSON 語法正確、沒有多餘逗號、字串內沒有換行、每個 senses 都恰好有 3 個例句、每個英文例句都含有該單字、topics 都在清單內且不超過 5 個、輸出的字數等於輸入字數。
10. 英文例句必須語法完整：名詞前該有 a／an／the 就要有（例如寫 "at the corner of the street"，不可寫 "at the corner of street"），所有格要有撇號，複合詞要有連字號。輸出前逐句檢查一次。
11. emoji 只在「該字第一義項只有一種明顯對應」時才填。只要還有第二種常見聯想就填 null（例如 wild 不填 🦁、hall 不填 🏛️、cool 不填 😎）；也不要用太新的 emoji（例如 🛞），避免舊手機顯示成方框。
12. 中文翻譯必須忠實對應英文原句：不可加入原文沒有的詞，不可漏譯，不可用贅詞（例如「打聽詢問」「排隊隊伍」）。zh 義項之間不可重複同義詞。
13. 常見且重要的詞性不可漏列（例如 what 同時是代名詞與限定詞）；但不常見或勉強的詞性不要為了湊數而列出。若某個詞性只能造出不自然的例句，就不要列該詞性。

14. 例句不要加入湊字數的贅字（例如 every single、句尾多餘的 today、同義重複的形容詞）；不要用太文學化、需要特殊背景的比喻。例句的情境盡量像會考、學測、多益會出現的校園、家庭、購物、旅行、公告、電子郵件、辦公室對話。
15. 複合字、衍生字不算有出現該單字（例如 shot 不能只靠 gunshot，fire 不能只靠 campfire）；例句中請直接使用該單字本身或其時態、單複數、比較級變化形。
16. 中文翻譯的人稱要與英文一致（They 不可譯成「他」）；動物用「牠」；用詞符合台灣慣用語。
17. 同一詞性的 3 個例句要有不同的搭配或情境；不可 3 句都是同一種場景或句型。

18. 例句一律使用中性的校園、家庭、購物、旅行、辦公室情境；遇到 kill、attack、fight、weapon、death 等字時，優先選用無暴力的義項與情境（例如 kill 用 kill time「打發時間」，death 用「調查死亡原因」），不要出現血腥、毆打、犯罪細節。
19. 每個義項的 zh 必須涵蓋該義項 3 個例句實際用到的所有意思（例如 mouth 用到「河口」，zh 就要有「河口」）。例句的詞性必須與該義項的 pos 一致（例如 pos 是 adv. 就不要用形容詞或名詞的用法）。

20. emoji 版本：不可使用 Unicode Emoji 13.0 以後新增的 emoji（舊手機會顯示成方框）。常見的有：🪨 🛗 🪚 🫖 🪳 🫘 🪪 🛝 🫥 🪵 🥲 🥸 🤌 🫀 🫁 🥷 🫂 🦬 🦣 🦫 🦤 🪶 🦭 🪲 🪰 🪱 🪴 🫐 🫒 🫑 🫓 🫔 🫕 🧋 🛖 🛻 🛼 🪄 🪅 🪆 🪡 🪢 🩴 🪖 🪗 🪘 🪙 🪃 🪛 🪝 🪜 🪞 🪟 🪠 🪤 🪒 🪧，以及 2021 年以後新增的所有 emoji。不確定某個 emoji 是不是新的，就填 null。
21. emoji 不可重複：`used_emoji.txt`「已用過的 emoji」清單裡的 emoji，除非該字與原本使用它的字是近義詞，否則一律填 null。同一批內也不要重複。emoji 必須對應「第一個 senses 的第一個意思」；若它只對應第二個詞性或第二個意思（例如 court 用 ⚖️、hop 用 🐰），填 null。
22. 例句中的目標字必須「單獨成詞」：不可只靠含連字號的複合詞（例如 billion-dollar、user-friendly、eco-friendly 不算有出現 billion、user、eco），也不可只靠合成字（toothpaste、painkiller 不算 paste、pain）。一般複合名詞若本身就是單字（例如 toothbrush 的例句用 toothbrush）則沒問題。
23. 台灣用語補充：安全帽（不用頭盔）、制服（不用校服）、塞車（不用堵塞）、事業／專案（不用項目）、攜帶式、新創公司、已開發國家、牧場、後背包、公尺、攝氏、秘密（統一用「秘」）、捷運（指台北捷運時）、地鐵只在指倫敦等國外地鐵時使用。
24. 禁用贅字：every single、句尾的 today、daily、anytime（除非它就是目標字）、同義重複的形容詞。
25. topics 以 1～3 個為原則（規格上限是 5），只列真正相關的；動物不要附「植物與自然」（除非是植物相關動物行為）；「抽象概念與其他」只能單獨使用。
26. image_query 一律 1～3 個英文字，且必須描述第一個 senses 的第一個意思（例如 record 第一義是「紀錄」，就不要寫成唱片）。
27. 輸出檔案之外，在回報檔 `reports/N####_A_done.md` 的 `GATE-A:` 行只寫一行判定：`GATE-A: PASS｜筆數 N/N｜順序一致｜emoji null M 個`；若筆數或順序不符、或有單字無法處理，寫 `GATE-A: FAIL｜原因`。

## 已用過的 emoji

讀 repo 根目錄的 `used_emoji.txt`（每行 `emoji(word)`，括號內是第一個用它的字）。不要憑記憶判斷哪些用過。

## 單筆範例（僅示範格式，請勿照抄內容）

{"word":"light","senses":[
{"pos":"n.","zh":"光；光線；燈","examples":[
{"en":"The light in the room was too dim to read by.","zh":"房間裡的光線太暗，沒辦法閱讀。"},
{"en":"Please turn off the light before you leave.","zh":"離開前請關燈。"},
{"en":"Sunlight is the main source of light on Earth.","zh":"陽光是地球上光線的主要來源。"}]},
{"pos":"adj.","zh":"輕的；淺色的；清淡的","examples":[
{"en":"This backpack is light enough for a child to carry.","zh":"這個背包很輕，小孩也背得動。"},
{"en":"She wore a light blue dress to the party.","zh":"她穿了一件淺藍色洋裝去參加派對。"},
{"en":"We had a light lunch because we were not very hungry.","zh":"我們不太餓，所以午餐吃得很清淡。"}]},
{"pos":"v.","zh":"點燃；照亮","examples":[
{"en":"He used a match to light the candle.","zh":"他用火柴點燃蠟燭。"},
{"en":"Fireworks lit up the night sky.","zh":"煙火照亮了夜空。"},
{"en":"The moon lit the path through the forest.","zh":"月光照亮了穿過森林的小徑。"}]}
],"topics":["日常生活","科學"],"emoji":"💡","image_query":"glowing light bulb"}

## 本次任務

本輪編號與單字清單**不再貼在這裡**：編號來自 `state.json` 的 `round`，單字來自 `vocab/vocab_####.json` 的 `words[].word`，依檔內順序處理全部 `count` 個字。

## 回報檔格式 `reports/N####_A_done.md`

前段為固定欄位（每行 `KEY: value`），`---` 之後為自由文字（不超過 15 行）：
```
ROUND: N0001
STAGE: A
AGENT: claude
ATTEMPT: 1
OUTPUT: out_A/N0001A_vocab_0001.json
GATE-A: PASS｜筆數 50/50｜順序一致｜emoji null 7 個
MODEL: （若你知道自己是哪個模型與思考程度就填，例如 claude-sonnet-5-5 / medium；不知道填 unknown）
REPORTED_AT: 2026-11-01T10:00:00+08:00
---
（自由文字：有 error 的單字、自檢結果、備註）
```
