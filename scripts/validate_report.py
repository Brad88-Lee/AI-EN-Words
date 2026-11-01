#!/usr/bin/env python3
"""解析並驗證 AI 的回報檔 reports/N####_X_done.md（HANDOFF §5.3）。解析寬鬆：KEY 大小寫、全形冒號、
空白、JSON 區塊有無 ```json 圍欄皆可。
用法：python3 scripts/validate_report.py 回報檔.md --stage C --round 0001 --attempt 1 [--allow-human] [--json out.json]
錯誤分三類（kind）：noncompliant（AGENT 不合法，不計 attempt）、stale（ROUND／STAGE／ATTEMPT 與 state 不符，不計 attempt）、
content（欄位缺漏、自報 FAIL、C 的結構化區塊缺少或格式錯，計 attempt）。有任何錯誤結束碼為 1。"""
import argparse, json, re, sys

AGENTS = {'A': {'claude'}, 'B': {'codex'}, 'C': {'claude'}}
BLOCK_KEYS = ('a_count', 'c_count', 'applied', 'skipped', 'extra_changes', 'nulls')
KV = re.compile(r'^\s*([A-Za-z][A-Za-z0-9_-]*)\s*[:：]\s*(.*?)\s*$')


def parse_report(text):
    """回傳 (fields, block, block_error)。fields 的 key 一律大寫。"""
    lines = text.splitlines(); fields = {}; rest = []; in_front = True
    for i, ln in enumerate(lines):
        if in_front and re.match(r'^\s*---+\s*$', ln):
            in_front = False; rest = lines[i + 1:]; break
        if in_front:
            m = KV.match(ln)
            if m: fields[m.group(1).upper()] = m.group(2)
    tail = '\n'.join(rest); block = None; err = None
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', tail, flags=re.S)
    cand = m.group(1) if m else None
    if cand is None:
        j = tail.find('{')
        if j >= 0: cand = tail[j:]
    if cand is not None:
        try: block, _ = json.JSONDecoder().raw_decode(cand)
        except json.JSONDecodeError as e: err = f'結構化 JSON 區塊無法解析：{e.msg}'
    return fields, block, err


def validate(text, stage, rnd, attempt, allow_human=False):
    fields, block, block_err = parse_report(text); errors = []
    def add(kind, msg): errors.append({'kind': kind, 'msg': msg})
    exp_round = f'N{rnd}'
    if re.sub(r'^[Nn]', '', fields.get('ROUND', '').strip()) != rnd: add('stale', f'ROUND 應為 {exp_round}，收到 {fields.get("ROUND") or "（缺）"}')   # N0001／0001／n0001 皆可
    if fields.get('STAGE', '').upper() != stage: add('stale', f'STAGE 應為 {stage}，收到 {fields.get("STAGE") or "（缺）"}')
    m_ag = re.match(r'(?i)\s*(claude|codex|human)', fields.get('AGENT', ''))
    ag = m_ag.group(1).lower() if m_ag else fields.get('AGENT', '').lower()   # 「Claude Code」「codex (GPT)」取前綴
    ok_agents = AGENTS[stage] | ({'human'} if allow_human else set())
    if ag not in ok_agents: add('noncompliant', f'AGENT 應為 {sorted(ok_agents)} 之一，收到 {ag or "（缺）"}')
    at = fields.get('ATTEMPT', '')
    if not re.fullmatch(r'\d+', at): add('stale', f'ATTEMPT 缺少或不是整數：{at or "（缺）"}')
    elif int(at) != attempt: add('stale', f'ATTEMPT 應為 {attempt}，收到 {at}')
    out_exp = f'out_{stage}/N{rnd}{stage}_vocab_{rnd}.json'
    gate = fields.get(f'GATE-{stage}', '')
    self_fail = bool(re.match(r'(?i)^FAIL', gate))
    if not gate: add('content', f'缺 GATE-{stage} 行')
    elif not re.match(r'(?i)^(PASS|FAIL)', gate): add('content', f'GATE-{stage} 格式錯：{gate[:40]}')
    if self_fail: add('content', f'AI 自報 GATE-{stage} FAIL：{gate}')
    if not self_fail and fields.get('OUTPUT', '') != out_exp: add('content', f'OUTPUT 應為 {out_exp}，收到 {fields.get("OUTPUT") or "（缺）"}')
    if stage == 'C' and not self_fail:
        if block_err: add('content', block_err)
        elif not isinstance(block, dict): add('content', '缺少結構化 JSON 區塊')
        else:
            for k in BLOCK_KEYS:
                if k not in block: add('content', f'結構化區塊缺 {k}')
            for k in ('applied', 'skipped', 'extra_changes', 'nulls'):
                v = block.get(k)
                if v is None: continue
                if not isinstance(v, list): add('content', f'{k} 必須是陣列'); continue
                for it in v:
                    if not (isinstance(it, dict) and isinstance(it.get('word'), str) and isinstance(it.get('path'), str)):
                        add('content', f'{k} 內有項目缺 word／path：{str(it)[:60]}'); break
            for k in ('a_count', 'c_count'):
                if k in block and not isinstance(block[k], int): add('content', f'{k} 必須是整數')
    return {'ok': not errors, 'self_fail': self_fail, 'errors': errors, 'fields': fields, 'block': block}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('report'); ap.add_argument('--stage', required=True, choices='ABC')
    ap.add_argument('--round', required=True, help='四位數，例如 0001'); ap.add_argument('--attempt', type=int, required=True)
    ap.add_argument('--allow-human', action='store_true'); ap.add_argument('--json', dest='jsonout')
    a = ap.parse_args()
    try: text = open(a.report, encoding='utf-8').read()
    except OSError as e: sys.exit(f'讀不到回報檔：{e}')
    r = validate(text, a.stage, a.round, a.attempt, a.allow_human)
    for e in r['errors']: print(f"[{e['kind']}] {e['msg']}")
    if r['ok']: print('回報檔格式 OK')
    if a.jsonout: json.dump(r, open(a.jsonout, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.exit(0 if r['ok'] else 1)


if __name__ == '__main__':
    main()
