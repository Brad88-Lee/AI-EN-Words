#!/usr/bin/env python3
"""check_batch.py 的補強版（備用）：只做 check_batch.py 沒做的、客觀可程式化的檢查。
用法：python3 check_extra.py 單字.json [--history 已匯入檔1.json 已匯入檔2.json ...] [--out 報告.md]
需要：pip install emoji --break-system-packages
檢查：Emoji 13+ 或不被辨識／批內與歷史重複 emoji／大陸與非台灣用語／例句只靠複合詞含目標字／a-an／贅字／topics 太多／全形省略號。
輸出分兩級：ERROR（匯入前應改）與 WARN（建議人工看）。"""
import json,re,sys,os,glob,argparse,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import emoji as E
import wordforms
import taiwan_terms

ELL='⋯⋯'


FILLER=[r'\bevery single\b',r'\banytime\b',r'\bdaily\b']
forms=wordforms.forms
def expand(paths):
    """--history 可給檔案、目錄（取其中所有 *.json）或萬用字元。"""
    out=[]
    for p in paths:
        if os.path.isdir(p): out+=sorted(glob.glob(os.path.join(p,'*.json')))
        elif any(c in p for c in '*?['): out+=sorted(glob.glob(p))
        else: out.append(p)
    return out
def load(p):
    raw=open(p,encoding='utf-8').read().strip()
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
    d=json.loads(raw); return d if isinstance(d,list) else d.get('words',d)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('json'); ap.add_argument('--history',nargs='*',default=[]); ap.add_argument('--out'); ap.add_argument('--json',dest='jsonout',help='把錯誤與警告寫成 JSON（給 error_signature.py 用）'); a=ap.parse_args()
    data=load(a.json)
    hist=collections.defaultdict(list)
    for h in expand(a.history):
        for x in load(h):
            if isinstance(x,dict) and x.get('emoji'): hist[x['emoji']].append(x['word'])
    batch=collections.defaultdict(list)
    for x in data:
        if x.get('emoji'): batch[x['emoji']].append(x['word'])
    out=[]
    def add(l,w,m): out.append((l,w,m))
    for d in data:
        w=d.get('word','?'); em=d.get('emoji')
        if em:
            info=E.EMOJI_DATA.get(em) or E.EMOJI_DATA.get(em.replace('️',''))
            if not info: add('ERROR',w,f'emoji 不被辨識（可能不是單一 emoji）：{em}')
            elif info['E']>=13: add('ERROR',w,f'Emoji {info["E"]}（舊手機會顯示方框）：{em}')
            others=[x for x in batch[em] if x!=w]+[x for x in hist.get(em,[]) if x!=w]
            if others: add('WARN',w,f'emoji {em} 與其他字重複：{",".join(dict.fromkeys(others))}（近義可保留，無關請改 null）')
        tp=d.get('topics') or []
        if len(tp)>3: add('WARN',w,f'topics {len(tp)} 個，建議 ≤3')
        fl=forms(w)
        for si,s in enumerate(d.get('senses',[])):
            zh=s.get('zh','')
            for t,note in taiwan_terms.hits([zh]+[e.get('zh','') for e in s.get('examples',[])],d.get('topics')):
                add('WARN',w,f's{si} 可能非台灣用語：{t}'+(f'（{note}）' if note else ''))
            if ELL in json.dumps(s,ensure_ascii=False): add('WARN',w,f's{si} 使用「⋯⋯」，專案慣例是「…」')
            for ei,e in enumerate(s.get('examples',[])):
                en=e.get('en',''); toks=re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*",en)
                low=[t.lower().replace('’',"'") for t in toks]
                standalone=any(t in fl for t in low)
                if not standalone:
                    inside=[t for t in low if w.lower() in t]
                    if inside: add('WARN',w,f's{si}e{ei} 目標字只出現在複合詞內（{inside[0]}），會影響畫面標示：{en[:60]}')
                for m in re.finditer(r"\b(a|an)\s+([A-Za-z]+)(-?)",en,flags=re.I):
                    art,orig,hy=m.group(1),m.group(2),m.group(3)
                    if not wordforms.article_ok(art,orig.lower(),hy=='-',orig): add('WARN',w,f's{si}e{ei} 冠詞可能不對：{art.lower()} {orig.lower()}')
                for f in FILLER:
                    if w.lower() in f: continue
                    if re.search(f,en,flags=re.I): add('WARN',w,f's{si}e{ei} 疑似贅字：{re.search(f,en,flags=re.I).group(0)}')
                if re.search(r'\btoday[.!?]?$',en.strip(),flags=re.I): add('WARN',w,f's{si}e{ei} 句尾 today')
    err=[x for x in out if x[0]=='ERROR']; wr=[x for x in out if x[0]=='WARN']
    txt=[f'# 補強檢查：{a.json}\n',f'{len(data)} 字；ERROR {len(err)}；WARN {len(wr)}\n','## ERROR']+[f'- {w}：{m}' for l,w,m in err]+['\n## WARN']+[f'- {w}：{m}' for l,w,m in wr]
    t='\n'.join(txt)
    if a.out: open(a.out,'w',encoding='utf-8').write(t)
    print(t)
    if a.jsonout:
        json.dump({'errors':[{'src':'check_extra','word':w,'msg':m} for l,w,m in err],'warns':[{'src':'check_extra','word':w,'msg':m} for l,w,m in wr]},open(a.jsonout,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    sys.exit(1 if err else 0)
main()
