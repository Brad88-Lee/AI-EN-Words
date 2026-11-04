ROUND: N0058
STAGE: A
AGENT: claude
ATTEMPT: 1
OUTPUT: out_A/N0058A_vocab_0058.json
GATE-A: PASS｜筆數 50/50｜順序一致｜emoji null 49 個
MODEL: claude-sonnet-5-5 / unknown
REPORTED_AT: 2026-11-04T08:30:00+08:00
---
eq 為縮寫、非常見單字，依規則 7 輸出 error 物件（emoji 不計入 null 49 個，其餘 49 字皆 null）。
erotic 以中性校園／博物館情境撰寫。
自檢：check_batch.py 僅 eq 的 error 提示；check_extra.py ERROR 0、WARN 0。
