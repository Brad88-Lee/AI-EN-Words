ROUND: N0027
STAGE: A
AGENT: claude
ATTEMPT: 1
OUTPUT: out_A/N0027A_vocab_0027.json
GATE-A: PASS｜筆數 50/50｜順序一致｜emoji null 48 個
MODEL: claude-sonnet-5-5 / unknown
REPORTED_AT: 2026-11-03T14:30:00+08:00
---
- india 依規則 7 輸出 error 物件（專有名詞，國名），check_batch 會將其列為 error，請總管／人工判定。
- 其餘 49 字中僅 heartbreak 填 💔，其餘 emoji 皆為 null（多數已被 used_emoji 佔用或不明確）。
- 自檢：check_extra.py ERROR 0／WARN 0；check_batch.py 僅 india 一筆 error。
