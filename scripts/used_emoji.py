#!/usr/bin/env python3
"""產生「已用過的 emoji」清單（每行 `emoji(第一個用它的單字)`），給 used_emoji.txt 與 A、B prompt。
用法：python3 scripts/used_emoji.py 檔案或萬用字元... [--out used_emoji.txt] [--keep-all]
預設略過 Emoji 13 以後或不被辨識的 emoji（它們不該出現在資料庫；--keep-all 則全部列出）。
需要：python3 -m pip install emoji"""
import argparse, glob, json, os, re, sys
import emoji as E

def load(p):
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', open(p, encoding='utf-8').read().strip())
    d = json.loads(raw)
    return d if isinstance(d, list) else d.get('words', d)

def expand(pats):
    out = []
    for p in pats:
        if os.path.isdir(p): out += sorted(glob.glob(os.path.join(p, '*.json')))
        elif any(c in p for c in '*?['): out += sorted(glob.glob(p))
        else: out.append(p)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('paths', nargs='+'); ap.add_argument('--out'); ap.add_argument('--keep-all', action='store_true')
    a = ap.parse_args(); seen = {}; skipped = []
    for f in expand(a.paths):
        for x in load(f):
            e = x.get('emoji') if isinstance(x, dict) else None
            if not e or e in seen: continue
            info = E.EMOJI_DATA.get(e) or E.EMOJI_DATA.get(e.replace('️', ''))
            if not a.keep_all and (not info or info['E'] >= 13): skipped.append((x['word'], e)); continue
            seen[e] = x['word']
    txt = '\n'.join(f'{e}({w})' for e, w in seen.items()) + '\n'
    if a.out: open(a.out, 'w', encoding='utf-8').write(txt)
    else: sys.stdout.write(txt)
    print(f'# 共 {len(seen)} 個；略過 Emoji 13+／不被辨識 {len(skipped)} 個', file=sys.stderr)

main()
