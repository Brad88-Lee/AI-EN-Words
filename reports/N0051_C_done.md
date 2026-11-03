ROUND: N0051
STAGE: C
AGENT: claude
ATTEMPT: 1
OUTPUT: out_C/N0051C_vocab_0051.json
GATE-C: PASS｜筆數 50/50｜套用 35｜跳過 2｜null 1/1
MODEL: unknown
REPORTED_AT: 2026-11-04T03:30:00+08:00
---
```json
{"a_count": 50, "c_count": 50, "applied": [{"word": "agitation", "path": "senses[0].zh"}, {"word": "aide", "path": "senses[0].zh"}, {"word": "airlift", "path": "image_query"}, {"word": "alarming", "path": "senses[0].zh"}, {"word": "alarming", "path": "senses[0].examples[0].en"}, {"word": "alarming", "path": "senses[0].examples[0].zh"}, {"word": "alleged", "path": "senses[0].examples[0].zh"}, {"word": "allied", "path": "senses[0].zh"}, {"word": "alloy", "path": "senses[1].zh"}, {"word": "alloy", "path": "image_query"}, {"word": "ambush", "path": "senses[1].zh"}, {"word": "ambush", "path": "senses[1].examples[0].zh"}, {"word": "amends", "path": "senses[0].zh"}, {"word": "amnesty", "path": "senses[0].zh"}, {"word": "angler", "path": "senses[0].zh"}, {"word": "antarctic", "path": "senses[0].examples[2].en"}, {"word": "antarctic", "path": "senses[0].examples[2].zh"}, {"word": "appall", "path": "senses[0].examples[1].en"}, {"word": "appall", "path": "senses[0].examples[1].zh"}, {"word": "apparatus", "path": "senses[0].zh"}, {"word": "apparatus", "path": "senses[0].examples[2].en"}, {"word": "apparatus", "path": "senses[0].examples[2].zh"}, {"word": "apprehension", "path": "senses[0].zh"}, {"word": "aptitude", "path": "senses[0].zh"}, {"word": "architectural", "path": "senses[0].examples[1].en"}, {"word": "architectural", "path": "senses[0].examples[1].zh"}, {"word": "arctic", "path": "senses[1].examples[0].en"}, {"word": "arctic", "path": "senses[1].examples[0].zh"}, {"word": "ascribe", "path": "senses[0].zh"}, {"word": "assignment", "path": "senses[0].examples[2].en"}, {"word": "assignment", "path": "senses[0].examples[2].zh"}, {"word": "asylum", "path": "senses[0].zh"}, {"word": "atm", "path": "senses[0].examples[2].en"}, {"word": "atm", "path": "senses[0].examples[2].zh"}, {"word": "atrocity", "path": "senses[0].zh"}], "skipped": [{"word": "antenna", "path": "senses[0].examples[2].en", "reason": "改為 antennae 後目標字只以變化形出現，check_extra 警告影響標示，維持原稿"}, {"word": "antenna", "path": "senses[0].examples[2].zh", "reason": "改為 antennae 後目標字只以變化形出現，check_extra 警告影響標示，維持原稿"}], "extra_changes": [], "nulls": [{"word": "airlift", "path": "image_query"}]}
```
---
A 50 筆、C 50 筆。套用 35、跳過 2（antenna 例句 3 en/zh，理由見上）。額外修改 0。airlift 的 image_query 依 B 設為 null。
