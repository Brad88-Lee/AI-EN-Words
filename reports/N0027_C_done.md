ROUND: N0027
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0027C_vocab_0027.json
GATE-C: PASS｜筆數 50/50｜套用 11｜跳過 1｜null 0/0
MODEL: unknown
REPORTED_AT: 2026-11-03T16:00:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "grandchild", "path": "senses[0].zh"}, {"word": "grandchild", "path": "senses[0].examples[0].zh"}, {"word": "grandchild", "path": "senses[0].examples[1].zh"}, {"word": "grandchild", "path": "senses[0].examples[2].zh"}, {"word": "hiker", "path": "senses[0].examples[1].zh"}, {"word": "hopefully", "path": "senses[0].examples[2].zh"}, {"word": "impersonal", "path": "senses[0].zh"}, {"word": "informed", "path": "senses[0].zh"}, {"word": "lavatory", "path": "senses[0].examples[1].zh"}, {"word": "long-standing", "path": "senses[0].examples[2].zh"}, {"word": "lorry", "path": "senses[0].examples[2].zh"}], "skipped": [{"word": "headset", "path": "image_query", "reason": "原值 headset with microphone 僅 3 字，符合上限，B 的理由不成立，不改"}], "extra_changes": [], "nulls": []}
```
---
A 50 筆、C 50 筆。B 共 12 筆 issue，套用 11、跳過 1（headset image_query：原值僅 3 字，B 理由不成立）。無額外修改、無 null。
