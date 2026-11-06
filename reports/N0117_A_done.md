ROUND: N0117
STAGE: A
AGENT: claude
ATTEMPT: 1
OUTPUT: out_A/N0117A_vocab_0117.json
GATE-A: PASS｜筆數 50/50｜順序一致｜emoji null 47 個
MODEL: claude-sonnet-5-5 / unknown
REPORTED_AT: 2026-11-06T20:32:11+08:00
---
第 46 筆 "n" 為單一字母，依規則 7 輸出 error 物件（其餘 49 字正常）。
自檢：check_batch.py 僅回報 n 的 error；check_extra.py ERROR 0、WARN 0。
