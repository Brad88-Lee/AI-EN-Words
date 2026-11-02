ROUND: N0001
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0001C_vocab_0001.json
GATE-C: PASS｜筆數 50/50｜套用 30｜跳過 1｜null 2/2
MODEL: unknown
REPORTED_AT: 2026-11-02T10:00:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "switch", "path": "senses[1].zh"}, {"word": "technology", "path": "senses[0].examples[1].en"}, {"word": "technology", "path": "senses[0].examples[1].zh"}, {"word": "tire", "path": "image_query"}, {"word": "tissue", "path": "senses[0].zh"}, {"word": "tone", "path": "senses[0].examples[1].zh"}, {"word": "wealth", "path": "senses[0].examples[1].en"}, {"word": "wealth", "path": "senses[0].examples[1].zh"}, {"word": "whoever", "path": "senses[0].examples[0].en"}, {"word": "whoever", "path": "senses[0].examples[0].zh"}, {"word": "wire", "path": "senses[1].examples[1].en"}, {"word": "wire", "path": "senses[1].examples[1].zh"}, {"word": "yam", "path": "emoji"}, {"word": "april", "path": "senses[0].examples[0].en"}, {"word": "april", "path": "senses[0].examples[0].zh"}, {"word": "autumn", "path": "senses[0].examples[2].en"}, {"word": "autumn", "path": "senses[0].examples[2].zh"}, {"word": "birthday", "path": "senses[0].examples[0].en"}, {"word": "birthday", "path": "senses[0].examples[0].zh"}, {"word": "chinese", "path": "senses[1].zh"}, {"word": "december", "path": "senses[0].examples[0].en"}, {"word": "december", "path": "senses[0].examples[0].zh"}, {"word": "december", "path": "senses[0].examples[1].en"}, {"word": "december", "path": "senses[0].examples[1].zh"}, {"word": "eight", "path": "senses[0].examples[0].en"}, {"word": "eight", "path": "senses[0].examples[0].zh"}, {"word": "eight", "path": "senses[0].examples[1].en"}, {"word": "eight", "path": "senses[0].examples[1].zh"}, {"word": "eight", "path": "senses[0].examples[2].en"}, {"word": "eight", "path": "senses[0].examples[2].zh"}], "skipped": [{"word": "actually", "path": "senses[0].zh", "reason": "fix 會刪掉「其實／事實上」，但例句 1、3 仍用到；改以額外修改補上「真的」並保留原義項"}], "extra_changes": [{"word": "actually", "path": "senses[0].zh", "reason": "B 的 fix 會漏掉其實／事實上；改為保留原義並補上「真的」（例句 2）"}], "nulls": [{"word": "tire", "path": "image_query"}, {"word": "yam", "path": "emoji"}]}
```
---
A 50 筆、C 50 筆。套用 30（含 2 個 null：tire image_query、yam emoji）、跳過 1。
跳過：actually senses[0].zh——B 的 fix 刪掉「其實／事實上」，但例句仍用到；改以額外修改保留並補「真的」。
額外修改：actually senses[0].zh。
check_batch、check_extra 皆 ERROR 0、WARN 0。
