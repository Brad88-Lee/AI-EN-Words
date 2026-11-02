ROUND: N0009
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0009C_vocab_0009.json
GATE-C: PASS｜筆數 50/50｜套用 42｜跳過 0｜null 2/2
MODEL: unknown
REPORTED_AT: 2026-11-02T17:40:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "monthly", "path": "senses[1].examples[0].en"}, {"word": "monthly", "path": "senses[1].examples[0].zh"}, {"word": "monthly", "path": "senses[1].examples[2].en"}, {"word": "monthly", "path": "senses[1].examples[2].zh"}, {"word": "product", "path": "senses[0].zh"}, {"word": "scale", "path": "senses[0].zh"}, {"word": "scale", "path": "senses[1].zh"}, {"word": "scale", "path": "image_query"}, {"word": "volume", "path": "senses[0].zh"}, {"word": "volume", "path": "senses[0].examples[1].en"}, {"word": "volume", "path": "senses[0].examples[1].zh"}, {"word": "voter", "path": "senses[0].examples[0].en"}, {"word": "voter", "path": "senses[0].examples[0].zh"}, {"word": "weekly", "path": "senses[1].examples[1].en"}, {"word": "weekly", "path": "senses[1].examples[1].zh"}, {"word": "weekly", "path": "senses[1].examples[2].en"}, {"word": "weekly", "path": "senses[1].examples[2].zh"}, {"word": "yearly", "path": "senses[1].examples[1].en"}, {"word": "yearly", "path": "senses[1].examples[1].zh"}, {"word": "yearly", "path": "senses[1].examples[2].en"}, {"word": "yearly", "path": "senses[1].examples[2].zh"}, {"word": "aboard", "path": "senses[0].examples[0].en"}, {"word": "aboard", "path": "senses[0].examples[0].zh"}, {"word": "aboard", "path": "senses[0].examples[2].zh"}, {"word": "aboard", "path": "senses[1].examples[0].en"}, {"word": "aboard", "path": "senses[1].examples[0].zh"}, {"word": "aboard", "path": "senses[1].examples[1].en"}, {"word": "aboard", "path": "senses[1].examples[1].zh"}, {"word": "accurate", "path": "senses[0].examples[2].en"}, {"word": "accurate", "path": "senses[0].examples[2].zh"}, {"word": "ache", "path": "senses[1].examples[0].en"}, {"word": "ache", "path": "senses[1].examples[0].zh"}, {"word": "ache", "path": "senses[1].examples[2].en"}, {"word": "ache", "path": "senses[1].examples[2].zh"}, {"word": "advanced", "path": "senses[0].examples[1].en"}, {"word": "advanced", "path": "senses[0].examples[1].zh"}, {"word": "advertise", "path": "senses[0].examples[2].zh"}, {"word": "afford", "path": "senses[0].examples[2].en"}, {"word": "afford", "path": "senses[0].examples[2].zh"}, {"word": "agriculture", "path": "image_query"}, {"word": "ambassador", "path": "senses[0].examples[1].en"}, {"word": "ambassador", "path": "senses[0].examples[1].zh"}], "skipped": [], "extra_changes": [], "nulls": [{"word": "scale", "path": "image_query"}, {"word": "agriculture", "path": "image_query"}]}
```
---
A 與 C 皆 50 筆。B 共 42 筆 issue 全數逐筆驗證後套用，無 uncertain、無跳過。
scale、agriculture 的 image_query 依 B 設為 null。自掃未發現需額外修改之處。
