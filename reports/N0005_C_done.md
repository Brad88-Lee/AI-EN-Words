ROUND: N0005
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0005C_vocab_0005.json
GATE-C: PASS｜筆數 50/50｜套用 42｜跳過 0｜null 1/1
MODEL: unknown
REPORTED_AT: 2026-11-02T13:30:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "you", "path": "senses[0].examples[0].zh"}, {"word": "your", "path": "senses[0].examples[1].en"}, {"word": "your", "path": "senses[0].examples[1].zh"}, {"word": "advise", "path": "senses[0].examples[2].zh"}, {"word": "alphabet", "path": "senses[0].examples[0].en"}, {"word": "alphabet", "path": "senses[0].examples[0].zh"}, {"word": "alphabet", "path": "senses[0].examples[1].en"}, {"word": "alphabet", "path": "senses[0].examples[1].zh"}, {"word": "apologize", "path": "senses[0].examples[0].zh"}, {"word": "besides", "path": "senses[1].examples[0].en"}, {"word": "besides", "path": "senses[1].examples[0].zh"}, {"word": "bitter", "path": "senses[0].zh"}, {"word": "bitter", "path": "senses[0].examples[1].zh"}, {"word": "bomb", "path": "senses[0].examples[2].en"}, {"word": "bomb", "path": "senses[0].examples[2].zh"}, {"word": "bomb", "path": "senses[1].examples[0].en"}, {"word": "bomb", "path": "senses[1].examples[0].zh"}, {"word": "cable", "path": "senses[0].examples[2].en"}, {"word": "cable", "path": "senses[0].examples[2].zh"}, {"word": "captain", "path": "image_query"}, {"word": "captain", "path": "senses[1].examples[2].en"}, {"word": "captain", "path": "senses[1].examples[2].zh"}, {"word": "closet", "path": "senses[0].examples[2].zh"}, {"word": "complain", "path": "senses[0].examples[1].en"}, {"word": "complain", "path": "senses[0].examples[1].zh"}, {"word": "confuse", "path": "senses[0].examples[0].en"}, {"word": "confuse", "path": "senses[0].examples[0].zh"}, {"word": "dawn", "path": "senses[1].examples[0].en"}, {"word": "dawn", "path": "senses[1].examples[0].zh"}, {"word": "dawn", "path": "senses[1].examples[2].en"}, {"word": "dawn", "path": "senses[1].examples[2].zh"}, {"word": "decorate", "path": "senses[0].zh"}, {"word": "decorate", "path": "senses[0].examples[0].zh"}, {"word": "decorate", "path": "senses[0].examples[1].en"}, {"word": "decorate", "path": "senses[0].examples[1].zh"}, {"word": "doughnut", "path": "senses[0].examples[0].en"}, {"word": "doughnut", "path": "senses[0].examples[0].zh"}, {"word": "doughnut", "path": "senses[0].examples[2].en"}, {"word": "doughnut", "path": "senses[0].examples[2].zh"}, {"word": "downtown", "path": "senses[0].examples[2].en"}, {"word": "downtown", "path": "senses[0].examples[2].zh"}, {"word": "downtown", "path": "senses[1].examples[2].zh"}], "skipped": [], "extra_changes": [], "nulls": [{"word": "captain", "path": "image_query"}]}
```
---
A 與 C 皆 50 筆。B 的 42 筆 issue 逐筆驗證後全數套用，無跳過、無額外修改。
captain 的 image_query 依 B 設為 null（1/1）。
