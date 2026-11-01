#!/usr/bin/env python3
"""把本次失敗的錯誤正規化成「錯誤簽章」（HANDOFF §8.2），用來偵測「同樣的錯再犯」。
輸入：check_batch.py／check_extra.py／diff_check.py／validate_b.py 的 --json 輸出（可多個）。
用法：python3 scripts/error_signature.py a.json b.json ... [--prev 上次簽章] [--out sig.json]
輸出 JSON：{"signature": 16 字元, "count": n, "items": [...], "same_as_prev": bool}。只取 errors，不含 warns。結束碼固定 0。"""
import argparse, hashlib, json, sys


def signature(error_lists):
    items = sorted({f"{e.get('src', '?')}|{e.get('word', '')}|{e.get('msg', '')}" for lst in error_lists for e in lst})
    sig = hashlib.sha256('\n'.join(items).encode('utf-8')).hexdigest()[:16] if items else 'none'
    return sig, items


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('files', nargs='+'); ap.add_argument('--prev'); ap.add_argument('--out')
    a = ap.parse_args(); lists = []
    for f in a.files:
        d = json.load(open(f, encoding='utf-8'))
        lists.append(d.get('errors', []) if isinstance(d, dict) else d)
    sig, items = signature(lists)
    res = {'signature': sig, 'count': len(items), 'items': items, 'same_as_prev': bool(a.prev) and a.prev == sig and sig != 'none'}
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out: open(a.out, 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
