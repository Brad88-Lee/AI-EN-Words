# scripts/

全部用 Python 3 執行。需要 `emoji` 套件：`python3 -m pip install emoji`（一律用 `python3 -m pip`）。其餘只用標準函式庫。
測試：`python3 -m unittest discover -s tests -v`（39 項，含 `tests/fixtures/real/` 的真實批次資料）。

| 腳本 | 用途 | 誰用 |
|---|---|---|
| `check_batch.py A.json vocab_####.json` | 格式與內容基本檢查（筆數、順序、pos、例句數、簡體字、topics、emoji 格式…）。有 ERROR 結束碼 1 | A／C 自檢、總管 |
| `check_extra.py X.json --history history/*.json master/*.json` | 補強檢查（Emoji 13+、重複 emoji、台灣用語、複合詞、a/an、贅字）。有 ERROR 結束碼 1 | A／C 自檢、總管 |
| `validate_report.py 回報檔 --stage X --round #### --attempt N` | 解析並驗證回報檔（寬鬆解析）；錯誤分 noncompliant／stale／content | 總管 |
| `validate_b.py A.json B.json` | 驗證 B 的輸出（結構、reviewed＝checked＝筆數、gate、每筆 issue 的 path 與 fix 型態） | 總管 |
| `diff_check.py A.json C.json B.json 回報檔` | C 的語意層 diff 比對（HANDOFF §9.3） | 總管 |
| `error_signature.py *.json [--prev 簽章]` | 把各檢查的 `--json` 錯誤正規化成簽章，偵測「同樣的錯再犯」（HANDOFF §8.2） | 總管 |
| `apply_b.py A.json B.json --out C.json [--json r.json]` | 用程式把 B 的修正套到 A（C 輸出模式「乙」的工具；甲模式下可用來交叉核對） | 備用 |
| `used_emoji.py 檔案… [--out used_emoji.txt]` | 產生「已用過的 emoji」清單，每行 `emoji(word)`；略過 Emoji 13+ | 總管 |
| `steward.py` ＋ `steward_finish.sh` | 總管的判斷與狀態機（validate-pr／apply-result／human-action／stall-check），由 `.github/workflows/steward.yml` 與 `stall_check.yml` 呼叫。說明見 `docs/STEWARD.md` | Actions |
| `make_vocab.py 總表.txt` | 從單字總表切出 `vocab/vocab_####.json` | 一次性 |

共用模組：`wordforms.py`（變化形、a/an）、`taiwan_terms.py`（大陸用語清單，兩支檢查共用）、`vocab_schema.py`（topics、詞性、issue 類型、path 格式）。

## `--json` 輸出格式（check_batch、check_extra、diff_check、validate_b）
```json
{"errors": [{"src": "check_extra", "word": "lamp", "msg": "Emoji 13（…）：🪨"}], "warns": []}
```
`error_signature.py` 只取 `errors`。

## 已知限制
- `check_batch.py` 的詞形比對對非連字號詞仍用前綴比對，可能漏報（例如變化形相近的別字）。
- 例句中文夾英文字母（`check_batch.py`）是 WARN，不是 ERROR：`Wi-Fi`、`iPhone` 這類合法混寫會被標到。
- 「大陸用語」清單只是 WARN，語意判斷由 B 負責。
