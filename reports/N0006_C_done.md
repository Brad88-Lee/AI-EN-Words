ROUND: N0006
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0006C_vocab_0006.json
GATE-C: PASS｜筆數 50/50｜套用 8｜跳過 0｜null 4/4
MODEL: unknown
REPORTED_AT: 2026-11-02T14:30:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "flashlight", "path": "senses[0].examples[0].zh"}, {"word": "geography", "path": "image_query"}, {"word": "gesture", "path": "senses[0].examples[0].zh"}, {"word": "gesture", "path": "senses[1].examples[2].zh"}, {"word": "humid", "path": "senses[0].zh"}, {"word": "invitation", "path": "image_query"}, {"word": "jazz", "path": "image_query"}, {"word": "kingdom", "path": "image_query"}], "skipped": [], "extra_changes": [], "nulls": [{"word": "geography", "path": "image_query"}, {"word": "invitation", "path": "image_query"}, {"word": "jazz", "path": "image_query"}, {"word": "kingdom", "path": "image_query"}]}
```
---
A 與 C 皆 50 筆。B 的 8 筆 issue 全數驗證後套用，無跳過、無額外修改。
geography、invitation、jazz、kingdom 的 image_query 依規則設為 null（4/4）。
