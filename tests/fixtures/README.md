# 連字號／撇號單字的測試案例（Phase 1 腳本用）

待生成字中有 71 個含連字號或撇號（`ma'am`、`o'clock`、`check-in`、`x-ray`、`e-mail`、`tug-of-war` …）。
這組案例用來確認 `check_batch.py`、`check_extra.py`（改版後）對這類字不會誤報、也不會漏報。

## 檔案
| 檔案 | 用途 |
|---|---|
| `hyphen_apostrophe_ok.json` | 8 字，全部寫對。期望：0 ERROR、0 WARN |
| `hyphen_apostrophe_bad.json` | 7 字，各藏一個問題。期望：每個問題都被抓到 |
| `*_words.txt` | 給舊版 `check_batch.py` 的單字清單（改讀 `vocab_####.json` 後可移除） |

每筆有 `_case`（情境）與 `_expect`（期望）欄位。檢查腳本只讀既有欄位，會忽略這兩個；**這些檔案不可匯入後台**。

## 用舊腳本實測的結果（check_batch.py／check_extra.py，Python 3.13、emoji 2.16.0）

### ok 組（期望全無 WARN）
| 字 | 實測 | 判定 |
|---|---|---|
| x-ray | check_extra：`an x` 冠詞可能不對 | **誤報**。X 唸 /eks/，`an X-ray` 才是對的 |
| x-ray | check_batch：zh 夾英文（`X 光`） | **規則衝突**。中文義合理含字母 X，要決定是否放行 |
| runner-up | check_batch：`runners-up` 可能不含該字 | **誤報**。不規則複數（`forms()` 只產生 `runner-ups`） |
| 其餘 5 字 | 無 WARN | 通過（含彎引號 `o’clock`、`ma’am`） |

### bad 組（期望每個問題都抓到）
| 案例 | 實測 | 判定 |
|---|---|---|
| e-mail 寫成 email | check_batch 抓到 | 通過 |
| sit-in 句子用了 sit-down | **沒抓到** | **漏報**。`contains()` 前綴比對太寬（`sit-` 就過） |
| trade-in 句子用了 trade-off | **沒抓到** | **漏報**。同上（`trade-` 就過） |
| `a x-ray` | **沒抓到** | **漏報**。x 被當子音 |
| `a up-to-date` | check_extra 抓到 | 通過 |
| part-time-worker（只靠更長複合詞） | check_batch、check_extra 都抓到 | 通過 |
| well-behaved 冒充 well-being | check_batch 抓到 | 通過 |

## 結論：改版時要處理的 4 件事
1. `check_extra.py` 的 a/an：`x`、`f`、`l`、`m`、`n`、`s` 等字母開頭的縮寫式詞（`X-ray`、`M-shaped`）要特例，避免誤報與漏報。
2. `check_extra.py` 的 `forms()`：連字號詞的複數可能出現在第一段（`runners-up`、`passers-by`、`sons-in-law`），需加規則。
3. `check_batch.py` 的 `contains()`：含連字號的目標字不要用前綴比對，改成整個詞（含變化形）比對。
4. `zh` 夾英文的 WARN：決定是否放行單一大寫字母（`X 光`）或常見縮寫。

以上都是舊腳本的行為；改版後請用這組案例再跑一次，期望 ok 組 0 WARN、bad 組全抓到。
