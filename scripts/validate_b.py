#!/usr/bin/env python3
"""驗證 B 的輸出檔 out_B/N####B_vocab_####.json（HANDOFF §9.2 的 B 列）。
用法：python3 scripts/validate_b.py A.json B.json [--count N] [--json out.json]
檢查：結構（batch、checked、reviewed、gate、issues）；checked＝reviewed 筆數＝A 筆數（或 --count）；gate.pass 為真；
每筆 issue 的 word 在 A 中、path 格式合法且在 A 中真實存在、severity 與 type 在允許值內、fix 的型態合法
（topics 為合法陣列、pos 為九種之一、emoji 為字串或 null、image_query 為 1～3 字或 null、其餘為非空字串；
非 uncertain 的 fix 只有 emoji／image_query 可為 null）。有 ERROR 結束碼為 1。"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vocab_schema as S


def validate_b(A, B, count=None):
    errs = []; warns = []
    def add(msg, word=''): errs.append({'src': 'validate_b', 'word': word, 'msg': msg})
    if not isinstance(B, dict): add('B 檔不是 JSON 物件'); return errs, warns
    for k in ('batch', 'checked', 'reviewed', 'gate', 'issues'):
        if k not in B: add(f'缺欄位 {k}')
    if errs: return errs, warns
    n = count if count is not None else len(A)
    if not (isinstance(B['batch'], str) and re.fullmatch(r'N\d{4}', B['batch'])): add(f"batch 應為 N####，收到 {B['batch']!r}")
    if len(A) != n: add(f'A 筆數 {len(A)} 不等於應有筆數 {n}')
    if B['checked'] != n: add(f"checked={B['checked']}，應為 {n}")
    if not isinstance(B['reviewed'], list) or len(B['reviewed']) != n: add(f"reviewed 筆數應為 {n}")
    elif sorted(B['reviewed']) != sorted(x['word'] for x in A): add('reviewed 的單字與 A 不一致')
    g = B['gate'] if isinstance(B['gate'], dict) else {}
    if g.get('pass') is not True: add(f"gate.pass 不是 true：{g.get('reason') or g}")
    idx = {x['word']: x for x in A}
    if not isinstance(B['issues'], list): add('issues 不是陣列'); return errs, warns
    for n_, i in enumerate(B['issues']):
        w = i.get('word', '') if isinstance(i, dict) else ''
        tag = f'issue#{n_}'
        if not isinstance(i, dict): add(f'{tag} 不是物件'); continue
        if w not in idx: add(f'{tag} word 不在 A 中：{w}', w); continue
        p = i.get('path', '')
        if not isinstance(p, str) or not S.PATH_RE.match(p): add(f'{tag} path 格式不合法：{p}', w); continue
        try: S.walk(idx[w], p)
        except (KeyError, IndexError, TypeError): add(f'{tag} path 在 A 中不存在：{p}', w); continue
        if i.get('severity') not in S.SEVERITIES: add(f"{tag} severity 不合法：{i.get('severity')}", w)
        if i.get('type') not in S.ISSUE_TYPES: add(f"{tag} type 不合法：{i.get('type')}", w)
        fx = i.get('fix', '\0missing'); unc = i.get('severity') == 'uncertain'
        if fx == '\0missing': add(f'{tag} 缺 fix 欄位', w); continue
        if fx is None:
            if not unc and p not in ('emoji', 'image_query'): add(f'{tag} fix 為 null 只允許用在 emoji／image_query：{p}', w)
            continue
        if unc:
            warns.append({'src': 'validate_b', 'word': w, 'msg': f'{tag} uncertain 但 fix 不是 null'}); continue
        if p == 'topics':
            if not (isinstance(fx, list) and 1 <= len(fx) <= 5 and all(t in S.TOPICS for t in fx) and not ('抽象概念與其他' in fx and len(fx) > 1)): add(f'{tag} topics fix 不合法：{fx}', w)
        elif p == 'emoji':
            if not isinstance(fx, str) or not fx: add(f'{tag} emoji fix 型態錯', w)
        elif p == 'image_query':
            if not (isinstance(fx, str) and 1 <= len(fx.split()) <= 3): add(f'{tag} image_query fix 不是 1～3 字', w)
        elif p.endswith('.pos'):
            if fx not in S.POS: add(f'{tag} pos fix 不合法：{fx}', w)
        elif not (isinstance(fx, str) and fx.strip()): add(f'{tag} fix 必須是非空字串', w)
    return errs, warns


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('A'); ap.add_argument('B'); ap.add_argument('--count', type=int); ap.add_argument('--json', dest='jsonout')
    a = ap.parse_args()
    A = json.load(open(a.A, encoding='utf-8')); B = json.load(open(a.B, encoding='utf-8'))
    errs, warns = validate_b(A, B, a.count)
    for e in errs: print('ERROR', e['msg'])
    for w in warns: print('WARN', w['msg'])
    print(f'ERROR {len(errs)}；WARN {len(warns)}')
    if a.jsonout: json.dump({'errors': errs, 'warns': warns}, open(a.jsonout, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
