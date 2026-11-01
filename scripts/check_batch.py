#!/usr/bin/env python3
"""檢查 AI 產出的單字 JSON。用法：
python3 check_batch.py 產出.json 單字清單 [--band 25] [--out 報告.md]
單字清單：vocab_####.json（{"words":[{"seq","word"}]}），或 txt（每行「序號. word」或純 word）。
有任何 ERROR 時結束碼為 1，否則 0。只做客觀檢查，不做語意判斷。"""
import json,re,sys,os,collections,argparse,statistics
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import wordforms
EXTRA_SIMP='晒怀'  # 在 Big5 內但屬簡體寫法的字，發現新的再補
def _in_big5(ch):
    try: ch.encode('big5'); return True
    except UnicodeEncodeError: return False
def simp(x):
    """含有不在 Big5（台灣標準字集）內的漢字，視為簡體字。晒、软、视 等會被抓到；床、吃、家具 等異體或正體字不會。"""
    return any(ch in EXTRA_SIMP or ('\u4e00'<=ch<='\u9fff' and not _in_big5(ch)) for ch in x)
TOPICS="日常生活、飲食、家庭與人際、學校與學習、工作與商業、金融與會計、健康與身體、情緒與性格、動物、植物與自然、天氣與環境、科技與網路、交通與旅行、運動與休閒、藝術與文化、社會與法律、科學、歷史與地理、抽象概念與其他".split('、')
POS={'n.','v.','adj.','adv.','prep.','conj.','pron.','det.','interj.'}
import taiwan_terms
# 「程序」「質量」等在科學/正式語境可能合理，列為 warn 而非 error
def variants(w):
    w=w.lower(); out={w}
    stems=[w]
    if w.endswith('e'): stems.append(w[:-1])
    if w.endswith('y'): stems.append(w[:-1]+'i')
    if len(w)>2 and w[-1]==w[-2]: pass
    if len(w)>=3: stems.append(w[:-1]+w[-1]*2)
    return stems
def has_english(zh):
    """中文欄位是否夾英文。允許 1～4 個大寫字母的獨立片段（X 光、T 恤、DNA）；小寫英文仍算。"""
    return bool(re.search(r'[A-Za-z]',re.sub(r'(?<![A-Za-z])[A-Z]{1,4}(?![A-Za-z])','',zh)))
def contains(en,w):
    if '-' in w: return wordforms.contains_exact(en,w)  # 連字號詞：整詞（含變化形）比對，不用前綴
    t=re.findall(r"[a-z'’-]+",en.lower().replace('’',"'"))
    stems=variants(w)
    for tok in t:
        for st in stems:
            if tok.startswith(st[:max(3,len(st)-2)]) and abs(len(tok)-len(st))<=4: return True
    # 不規則變化給 warn（呼叫端會標成 warn）
    return False
def load_list(p):
    if p.lower().endswith('.json'):
        d=json.load(open(p,encoding='utf-8'))
        return [x['word'].strip().lower() for x in d['words']]
    ws=[]
    for line in open(p,encoding='utf-8'):
        line=line.strip()
        if not line: continue
        m=re.match(r'^\d+[.、)]\s*(.+)$',line); ws.append((m.group(1) if m else line).strip().lower())
    return ws
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('json'); ap.add_argument('list'); ap.add_argument('--band',type=int,default=25); ap.add_argument('--out'); ap.add_argument('--json',dest='jsonout',help='把錯誤與警告寫成 JSON（給 error_signature.py 用）')
    a=ap.parse_args()
    exp=load_list(a.list)
    raw=open(a.json,encoding='utf-8').read().strip()
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
    truncated=False
    syntax_bad=[]
    try: data=json.loads(raw)
    except json.JSONDecodeError as e:
        # 改成逐行解析（精簡格式：每個單字一行），單行語法錯誤只影響該字
        data=[]; truncated=False
        for ln,line in enumerate(raw.split('\n')):
            t=line.strip().rstrip(',')
            if t in ('','[',']','```','```json'): continue
            try: data.append(json.loads(t))
            except json.JSONDecodeError as e2:
                m=re.search(r'"word"\s*:\s*"([^"]+)"',t)
                syntax_bad.append((m.group(1).lower() if m else f'(第{ln}行)',e2.msg,t))
        print(f'[警告] 整份 JSON 無法直接解析（{e.msg}），改為逐行解析：成功 {len(data)} 行，語法錯誤 {len(syntax_bad)} 行')
    issues=[]  # (idx0, word, severity, msg)
    def add(i,w,sev,msg): issues.append((i,w,sev,msg))
    for w,m,t in syntax_bad: add(exp.index(w) if w in exp else 0,w,'error',f'JSON 語法錯誤：{m}')
    got=[(d.get('word') or '').lower() if isinstance(d,dict) else '' for d in data]
    # 對照清單（缺漏、多餘、重複各報一次；順序只報一次，避免連鎖誤報）
    bad_words={w for w,_,_ in syntax_bad}
    missing=[w for w in exp if w not in set(got) and w not in bad_words]
    extra=[w for w in got if w and w not in set(exp)]
    if truncated: missing=[w for w in missing if exp.index(w)<len(got)]  # 截斷的缺漏不逐字報
    for w in missing: add(exp.index(w),w,'error','清單中的字沒有出現（漏字）')
    for w in extra: add(got.index(w),w,'error','不在清單內的字（多出或被改寫）')
    c=collections.Counter(got)
    for w,n in c.items():
        if n>1 and w: add(exp.index(w) if w in exp else got.index(w),w,'error',f'重複 {n} 次')
    common_got=[w for w in got if w in set(exp)]
    common_exp=[w for w in exp if w in set(got)]
    if common_got!=common_exp: add(0,'(整體)','error','順序與清單不一致')
    if len(got)<len(exp): print(f'[注意] 只有 {len(got)} / {len(exp)} 筆；缺 {len(exp)-len(got)} 筆（可能被截斷或漏字）')
    pos_of={w:i for i,w in enumerate(exp)}
    stats=[]  # per word: en_len mean, zh_len mean
    for i,d in enumerate(data):
        if not isinstance(d,dict): add(i,'?','error','不是物件'); continue
        w=(d.get('word') or '').lower()
        i=pos_of.get(w,i)
        if 'error' in d: add(i,w,'warn',f"AI 回報錯誤：{d['error']}"); continue
        senses=d.get('senses')
        if not isinstance(senses,list) or not 1<=len(senses)<=3: add(i,w,'error','senses 數量不是 1～3'); continue
        enl=[];zhl=[]
        seen_pos=set(); ml={}
        for si,s in enumerate(senses):
            pos=s.get('pos')
            if pos not in POS: add(i,w,'error',f's{si} pos 不合法：{pos}')
            if pos in seen_pos: add(i,w,'warn',f'詞性重複 {pos}')
            seen_pos.add(pos)
            zh=s.get('zh','')
            if not zh or has_english(zh): add(i,w,'warn',f's{si}.zh 空白或夾英文')
            ex=s.get('examples')
            if not isinstance(ex,list) or len(ex)!=3: add(i,w,'error',f's{si} 例句不是 3 句'); continue
            ens=[]
            for ei,e in enumerate(ex):
                en=e.get('en','');zz=e.get('zh','')
                ens.append(en.lower())
                enl.append(len(en.split())); zhl.append(len(zz))
                if not contains(en,w): add(i,w,'warn',f's{si}e{ei} 英文例句可能不含該字（變化形可能誤報）：{en[:50]}')
                if not 5<=len(en.split())<=25: add(i,w,'warn',f's{si}e{ei} 英文長度 {len(en.split())} 字')
                if simp(zz) or simp(zh): add(i,w,'error',f's{si}e{ei} 疑似簡體字')
                if re.search(r'[,;?!]',zz) or re.search(r'[一-鿿]\.',zz): add(i,w,'warn',f's{si}e{ei} 中文使用半形標點')
                for t,note in taiwan_terms.hits([zz,zh],d.get('topics')): ml[t]=note
                if has_english(zz): add(i,w,'warn',f's{si}e{ei} 例句中文夾英文：{zz[:30]}')
            if len(set(ens))<3: add(i,w,'error',f's{si} 例句重複')
        for t,note in ml.items(): add(i,w,'warn',f'可能大陸用語：{t}'+(f'（{note}）' if note else ''))
        tp=d.get('topics')
        if not isinstance(tp,list) or not 1<=len(tp)<=5: add(i,w,'error','topics 數量不對')
        else:
            for t in tp:
                if t not in TOPICS: add(i,w,'error',f'topics 不在清單：{t}')
            if '抽象概念與其他' in tp and len(tp)>1: add(i,w,'error','抽象概念與其他 不可並列')
        em=d.get('emoji')
        if em is not None and (not isinstance(em,str) or re.search(r'[A-Za-z一-鿿]',em) or len(em)>12): add(i,w,'error',f'emoji 格式：{em}')
        iq=d.get('image_query')
        if iq is not None and (not isinstance(iq,str) or not 1<=len(iq.split())<=3): add(i,w,'error',f'image_query 不是 1～3 字：{iq}')
        if enl: stats.append((i,statistics.mean(enl),statistics.mean(zhl),len(senses),sum(1 for _ in [0] if em is None)))
    # 分段統計
    B=a.band; n=len(exp); rows=[]
    for b in range(0,n,B):
        rng=range(b,min(b+B,n))
        got_n=sum(1 for i in rng if i<len(data))
        er=[x for x in issues if x[0] in rng and x[2]=='error']; wa=[x for x in issues if x[0] in rng and x[2]=='warn']
        st=[x for x in stats if x[0] in rng]
        rows.append((b+1,min(b+B,n),got_n,len(er),len(wa),
            round(statistics.mean(x[1] for x in st),1) if st else '',
            round(statistics.mean(x[2] for x in st),1) if st else '',
            round(statistics.mean(x[3] for x in st),2) if st else '',
            round(sum(1 for x in st if x[4])/len(st),2) if st else ''))
    out=[f'# 檢查報告：{a.json}\n',f'清單 {len(exp)} 字，收到 {len(data)} 筆{"（JSON 被截斷，已救回完整物件）" if truncated else ""}\n',
        '| 範圍 | 收到 | 錯誤 | 警告 | 例句平均字數 | 中譯平均字數 | 平均詞性數 | emoji 空值率 |','|---|---|---|---|---|---|---|---|']
    for r in rows: out.append(f'| {r[0]}–{r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} |')
    out.append('\n## 錯誤明細\n')
    for i,w,sev,m in sorted(issues):
        if sev=='error': out.append(f'- #{i+1} {w}：{m}')
    out.append('\n## 警告明細\n')
    for i,w,sev,m in sorted(issues):
        if sev=='warn': out.append(f'- #{i+1} {w}：{m}')
    txt='\n'.join(out)
    if a.out: open(a.out,'w',encoding='utf-8').write(txt)
    print(txt[:3500])
    if a.jsonout:
        json.dump({'errors':[{'src':'check_batch','word':w,'msg':m} for i,w,sev,m in sorted(issues) if sev=='error'],'warns':[{'src':'check_batch','word':w,'msg':m} for i,w,sev,m in sorted(issues) if sev=='warn']},open(a.jsonout,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    sys.exit(1 if any(x[2]=='error' for x in issues) else 0)
main()
