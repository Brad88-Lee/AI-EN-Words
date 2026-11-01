#!/usr/bin/env python3
"""把 B 的校正清單用程式套用到 A（取代 C 的「套用」工作，備用）。
用法：python3 apply_b.py A.json B.json --out 套用後.json [--report 報告.md]
規則（與 v2 的 C prompt 相同）：
 1. severity=uncertain → 不套用。
 2. fix=null：path 是 emoji / image_query 且非 uncertain → 設為 null；其他 path → 跳過。
 3. path 必須存在、型態要合理（字串／topics 陣列），否則跳過並列出原因。
 4. 同一 path 有多筆 → 取嚴重度較高者（同級取先出現者），其餘跳過。
 5. 英文例句被改、但同一位置的 .zh 沒有同時被改 → 列入「需人工確認中文」。
 6. 套用後：筆數、順序必須與 A 相同，否則報錯。
套用後請再跑 check_batch.py 與 check_extra.py。"""
import json,re,sys,argparse,copy,collections
SEV={'high':3,'medium':2,'low':1,'uncertain':0}
TOP="日常生活、飲食、家庭與人際、學校與學習、工作與商業、金融與會計、健康與身體、情緒與性格、動物、植物與自然、天氣與環境、科技與網路、交通與旅行、運動與休閒、藝術與文化、社會與法律、科學、歷史與地理、抽象概念與其他".split('、')
FUNC={'a','an','the','his','her','their','your','my','our','its','of','to','in','on','at','for','with','by','from','and','or','is','are','was','were','be','s'}
def content_changed(old,new):
    """英文改動是否牽涉實詞：只增減冠詞、所有格、連字號、標點等虛詞不算，不需要提醒中文要同步。"""
    tok=lambda t: collections.Counter(re.findall(r"[a-z]+",t.lower()))
    a,b=tok(old),tok(new); diff=(a-b)+(b-a)
    return any(w not in FUNC for w in diff)
def parse(p):
    return [(m.group(1) if m.group(1) else int(m.group(2))) for m in re.finditer(r'([A-Za-z_]+)|\[(\d+)\]',p)]
def walk(o,keys):
    for k in keys[:-1]: o=o[k]
    return o,keys[-1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('A'); ap.add_argument('B'); ap.add_argument('--out',required=True); ap.add_argument('--report'); ap.add_argument('--json',dest='jsonout',help='把套用結果寫成 JSON（applied／skipped／nulls）'); a=ap.parse_args()
    A=json.load(open(a.A,encoding='utf-8')); B=json.load(open(a.B,encoding='utf-8')); iss=B['issues'] if isinstance(B,dict) else B
    C=copy.deepcopy(A); idx={x['word']:x for x in C}
    applied=[];skipped=[];nulls=[];chg_en=set();chg_zh=set()
    best={}
    for n,i in enumerate(iss):
        k=(i['word'],i['path'])
        if k not in best or SEV[i['severity']]>SEV[best[k]['severity']]:
            if k in best: skipped.append((best[k],'同一欄位有更高嚴重度的建議'))
            best[k]=i
        else: skipped.append((i,'同一欄位已有較高或相同嚴重度的建議'))
    for (w,p),i in best.items():
        if i['severity']=='uncertain': skipped.append((i,'uncertain')); continue
        if w not in idx: skipped.append((i,'word 不在 A')); continue
        try: keys=parse(p); par,last=walk(idx[w],keys); cur=par[last]
        except Exception: skipped.append((i,'path 不存在')); continue
        fx=i['fix']
        if fx is None:
            if p in ('emoji','image_query'): par[last]=None; nulls.append((w,p)); applied.append(i)
            else: skipped.append((i,'fix 為 null 且非 emoji/image_query'))
            continue
        if p=='topics':
            if not(isinstance(fx,list) and 1<=len(fx)<=5 and all(t in TOP for t in fx) and not('抽象概念與其他' in fx and len(fx)>1)): skipped.append((i,'topics 不合法')); continue
        elif p=='image_query':
            if not(isinstance(fx,str) and 1<=len(fx.split())<=3): skipped.append((i,'image_query 不是 1~3 字')); continue
        elif p=='emoji':
            if not isinstance(fx,str): skipped.append((i,'emoji 型態錯')); continue
        elif not isinstance(fx,str): skipped.append((i,'fix 型態錯')); continue
        par[last]=fx; applied.append(i)
        if p.endswith('.en') and content_changed(cur,fx): chg_en.add((w,p[:-3]))
        if p.endswith('.zh'): chg_zh.add((w,p[:-3]))
    need=sorted(chg_en-chg_zh)
    assert [x['word'] for x in A]==[x['word'] for x in C] and len(A)==len(C)
    with open(a.out,'w',encoding='utf-8') as f:
        f.write('[\n'+',\n'.join(json.dumps(x,ensure_ascii=False,separators=(',',':')) for x in C)+'\n]\n')
    if a.jsonout:
        json.dump({'applied':[{'word':i['word'],'path':i['path']} for i in applied],
                   'skipped':[{'word':i['word'],'path':i['path'],'reason':why} for i,why in skipped],
                   'nulls':[{'word':w,'path':p} for w,p in nulls],
                   'need_zh_check':[{'word':w,'path':p} for w,p in need]},open(a.jsonout,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    r=[f'# apply_b 報告\n',f'A {len(A)} 字；B issues {len(iss)}；已套用 {len(applied)}；跳過 {len(skipped)}；emoji/image_query 設 null {len(nulls)}\n',
       '## 需人工確認中文（英文被改但中文沒跟著改）']+[f'- {w} {p}' for w,p in need]+['\n## 跳過清單']+[f"- {i['word']} {i['path']}（{why}）" for i,why in skipped]+['\n## 設為 null']+[f'- {w} {p}' for w,p in nulls]
    t='\n'.join(r)
    if a.report: open(a.report,'w',encoding='utf-8').write(t)
    print(t[:3000])
main()
