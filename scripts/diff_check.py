#!/usr/bin/env python3
"""C 的語意層 diff 比對（HANDOFF §9.3）：A 與 C 的每個欄位值差異，必須能被 B 的 issue 與回報檔解釋。
用法：python3 scripts/diff_check.py A.json C.json B.json 回報檔.md [--json out.json] [--out 報告.md]
規則：
 1. A、C 逐 word、逐 path 比較值（不比排版、鍵順序）。
 2. 有差異的 path 必須：(a) 在回報檔 applied，且對應 B 某個 severity≠uncertain 的 issue；(b) 是 (a) 中某個 .en 的同位置 .zh；
    (c) 在回報檔 extra_changes。否則 diff:unexpected。
 3. applied 的每個 path 必須真的有差異，否則 diff:claimed_not_applied。
 4. B 中 fix=null、severity≠uncertain、path 為 emoji／image_query 的每一筆，C 的值必須為 null，否則 diff:null_missing。
 5. skipped 的 path 必須無差異，否則 diff:skipped_changed。
 6. 筆數、順序必須與 A 相同；回報檔 a_count／c_count 必須相符。
有任何錯誤結束碼為 1。"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_report, vocab_schema


def load(p):
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', open(p, encoding='utf-8').read().strip())
    d = json.loads(raw)
    return d if isinstance(d, list) else d.get('words', d)


def diff_check(A, C, B, block):
    errs = []
    def add(code, word, path, msg): errs.append({'code': code, 'word': word, 'path': path, 'msg': f'diff:{code}:{word}.{path}' if path else f'diff:{code}:{word}' if word else f'diff:{code}', 'detail': msg})
    wa, wc = [x.get('word') for x in A], [x.get('word') for x in C]
    if len(A) != len(C): add('count', '', '', f'A {len(A)} 筆、C {len(C)} 筆')
    if wa != wc:
        add('order', '', '', 'C 的單字與順序和 A 不同')
        return errs
    if isinstance(block.get('a_count'), int) and block['a_count'] != len(A): add('report_count', '', '', f"回報檔 a_count={block['a_count']}，實際 {len(A)}")
    if isinstance(block.get('c_count'), int) and block['c_count'] != len(C): add('report_count', '', '', f"回報檔 c_count={block['c_count']}，實際 {len(C)}")
    issues = [i for i in (B.get('issues') if isinstance(B, dict) else B) or [] if isinstance(i, dict)]
    active = {(i['word'], i['path']) for i in issues if i.get('severity') != 'uncertain' and 'word' in i and 'path' in i}
    applied = {(x['word'], x['path']) for x in block.get('applied', [])}
    extra = {(x['word'], x['path']) for x in block.get('extra_changes', [])}
    skipped = {(x['word'], x['path']) for x in block.get('skipped', [])}
    nulls = {(x['word'], x['path']) for x in block.get('nulls', [])}
    diffs = set(); vals = {}
    for a, c in zip(A, C):
        fa, fc = vocab_schema.flatten(a), vocab_schema.flatten(c)
        for p in set(fa) | set(fc):
            if fa.get(p, '\0MISSING') != fc.get(p, '\0MISSING'):
                diffs.add((a['word'], p)); vals[(a['word'], p)] = fc.get(p)
    ok_a = applied & active
    allowed = set(ok_a) | extra
    for w, p in ok_a:
        if p.endswith('.en'): allowed.add((w, p[:-3] + '.zh'))
    for w, p in sorted(diffs - allowed): add('unexpected', w, p, '值有差異但不在 applied（且對應 B 的 issue）、也不在 extra_changes')
    for w, p in sorted(applied - diffs): add('claimed_not_applied', w, p, 'applied 宣稱已套用，但 A 與 C 的值相同')
    for w, p in sorted(skipped & diffs): add('skipped_changed', w, p, 'skipped 的欄位在 C 有差異')
    for i in issues:
        if i.get('severity') != 'uncertain' and i.get('fix') is None and i.get('path') in ('emoji', 'image_query'):
            w, p = i['word'], i['path']
            cw = next((c for c in C if c.get('word') == w), None)
            if cw is not None and cw.get(p) is not None: add('null_missing', w, p, f'B 要求把 {p} 設為 null，C 的值是 {cw.get(p)!r}')
    for w, p in sorted(nulls):
        cw = next((c for c in C if c.get('word') == w), None)
        if cw is None or cw.get(p) is not None: add('null_claimed_not_null', w, p, 'nulls 列了這個欄位，但 C 的值不是 null')
    return errs


def main():
    ap = argparse.ArgumentParser(); [ap.add_argument(x) for x in ('A', 'C', 'B', 'report')]; ap.add_argument('--json', dest='jsonout'); ap.add_argument('--out')
    a = ap.parse_args()
    fields, block, err = validate_report.parse_report(open(a.report, encoding='utf-8').read())
    if not isinstance(block, dict): sys.exit(f'回報檔缺少可解析的結構化區塊：{err or "找不到"}')
    for k in ('applied', 'skipped', 'extra_changes', 'nulls'): block.setdefault(k, [])
    B = json.load(open(a.B, encoding='utf-8'))
    errs = diff_check(load(a.A), load(a.C), B, block)
    lines = [f'# diff 比對：{a.C}', '', f'ERROR {len(errs)}', '']
    lines += [f"- {e['msg']}（{e['detail']}）" for e in errs]
    txt = '\n'.join(lines) + '\n'
    if a.out: open(a.out, 'w', encoding='utf-8').write(txt)
    print(txt)
    if a.jsonout: json.dump({'errors': [{'src': 'diff_check', 'word': e['word'], 'msg': e['msg']} for e in errs], 'warns': []}, open(a.jsonout, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
