ROUND: N0017
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0017C_vocab_0017.json
GATE-C: PASS｜筆數 50/50｜套用 38｜跳過 0｜null 2/2
MODEL: unknown
REPORTED_AT: 2026-11-02T12:00:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "missile", "path": "senses[0].examples[2].zh"}, {"word": "mob", "path": "senses[0].zh"}, {"word": "mobile", "path": "senses[0].zh"}, {"word": "mobile", "path": "senses[0].examples[2].zh"}, {"word": "motel", "path": "senses[0].examples[2].zh"}, {"word": "muscle", "path": "senses[0].examples[0].en"}, {"word": "muscle", "path": "senses[0].examples[0].zh"}, {"word": "native", "path": "senses[0].examples[0].en"}, {"word": "native", "path": "senses[0].examples[0].zh"}, {"word": "native", "path": "senses[1].examples[0].en"}, {"word": "native", "path": "senses[1].examples[0].zh"}, {"word": "navy", "path": "senses[0].examples[2].en"}, {"word": "navy", "path": "senses[0].examples[2].zh"}, {"word": "nickname", "path": "senses[1].examples[1].en"}, {"word": "nickname", "path": "senses[1].examples[1].zh"}, {"word": "oak", "path": "senses[0].examples[2].en"}, {"word": "oak", "path": "senses[0].examples[2].zh"}, {"word": "observe", "path": "senses[0].examples[0].zh"}, {"word": "observe", "path": "senses[0].examples[2].en"}, {"word": "observe", "path": "senses[0].examples[2].zh"}, {"word": "observe", "path": "image_query"}, {"word": "occasion", "path": "senses[0].zh"}, {"word": "odd", "path": "topics"}, {"word": "onto", "path": "senses[0].examples[0].en"}, {"word": "onto", "path": "senses[0].examples[0].zh"}, {"word": "opposite", "path": "senses[0].examples[2].en"}, {"word": "opposite", "path": "senses[0].examples[2].zh"}, {"word": "optimistic", "path": "senses[0].examples[0].en"}, {"word": "optimistic", "path": "senses[0].examples[0].zh"}, {"word": "oral", "path": "senses[0].examples[1].en"}, {"word": "oral", "path": "senses[0].examples[1].zh"}, {"word": "organic", "path": "senses[0].zh"}, {"word": "original", "path": "senses[1].zh"}, {"word": "outdoor", "path": "senses[0].examples[1].en"}, {"word": "outdoor", "path": "senses[0].examples[1].zh"}, {"word": "outline", "path": "image_query"}, {"word": "owe", "path": "senses[0].examples[0].en"}, {"word": "owe", "path": "senses[0].examples[0].zh"}], "skipped": [], "extra_changes": [], "nulls": [{"word": "observe", "path": "image_query"}, {"word": "outline", "path": "image_query"}]}
```
---
A 50 筆、C 50 筆。B 的 38 筆 issue 逐筆驗證後全數套用，無跳過。
observe、outline 的 image_query 依規則設為 null（2/2）。
英文例句修正皆含目標字，中文已隨 B 的 fix 同步。無額外修改。
