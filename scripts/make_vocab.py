#!/usr/bin/env python3
"""從「單字總表」(markdown 表格) 切出 vocab/vocab_####.json（HANDOFF §5.2）。
用法：python3 scripts/make_vocab.py 總表.txt [--out vocab] [--per 50] [--first-batch 5]
只取狀態為「待生成」的列，依表中順序（＝生成順序）切段；每輪 --per 字，最後一輪可不足。
批號：每 10 輪一批，從 --first-batch 起算。表格列格式：| 序號 | 狀態 | word | … |"""
import argparse, json, os, re, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('table'); ap.add_argument('--out', default='vocab')
    ap.add_argument('--per', type=int, default=50); ap.add_argument('--first-batch', type=int, default=5)
    a = ap.parse_args()
    rows = []
    for line in open(a.table, encoding='utf-8'):
        m = re.match(r'^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', line)
        if m and m.group(2) == '待生成':
            rows.append((int(m.group(1)), m.group(3).strip().lower()))
    if not rows: sys.exit('沒有找到「待生成」的列')
    seqs = [s for s, _ in rows]
    if seqs != list(range(seqs[0], seqs[0] + len(seqs))): sys.exit('序號不連續')
    words = [w for _, w in rows]
    if len(set(words)) != len(words): sys.exit('有重複單字')
    os.makedirs(a.out, exist_ok=True)
    total = (len(rows) + a.per - 1) // a.per
    for k in range(1, total + 1):
        chunk = rows[(k - 1) * a.per: k * a.per]
        d = {"round": f"{k:04d}", "batch": a.first_batch + (k - 1) // 10,
             "seq_from": chunk[0][0], "seq_to": chunk[-1][0], "count": len(chunk),
             "words": [{"seq": s, "word": w} for s, w in chunk]}
        with open(os.path.join(a.out, f'vocab_{k:04d}.json'), 'w', encoding='utf-8') as f:
            f.write('{"round":"%s","batch":%d,"seq_from":%d,"seq_to":%d,"count":%d,\n "words":[\n' % (d['round'], d['batch'], d['seq_from'], d['seq_to'], d['count']))
            f.write(',\n'.join(json.dumps(x, ensure_ascii=False, separators=(',', ':')) for x in d['words']))
            f.write('\n]}\n')
    print(f'{len(rows)} 字 → {total} 輪（{a.out}/）')

main()
