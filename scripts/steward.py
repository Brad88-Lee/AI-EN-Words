#!/usr/bin/env python3
"""總管（HANDOFF §3、§7～§9）的判斷與狀態機。GitHub Actions 只負責呼叫 git／gh，所有決策都在這裡，方便本機測試。

子命令
  validate-pr   唯讀。驗證一個 AI 交付的 PR，輸出 result.json（verdict 與錯誤）。
  apply-result  依 result.json 修改工作目錄（state.json、jobs.md、master/、attempts/、used_emoji.txt…），輸出 actions.json。
                verdict=pass 時，PR 必須已先合併進 main（輸出檔已在工作目錄）。
  human-action  人工動作：continue／redo／skip／imported。
  stall-check   逾時偵測（不計 attempt）。
  record-issue  把開好的 Issue 編號寫回 state.open_issue。

verdict：ignored（沒有任何 out_X／回報檔的 PR，例如開發或文件 PR，總管完全不處理）／pass／content_fail（計 attempt）／stale（過期交付）／noncompliant（AGENT 不合法）／rejected（改到允許路徑外或 fork），
後三者不計 attempt。所有時間由 --now 傳入（ISO 8601，+08:00），腳本不讀系統時鐘。
"""
import argparse, csv, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timedelta

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import diff_check, error_signature, validate_b, validate_report  # noqa: E402

# 暫定時限（HANDOFF §7，Phase 2 量測後定）。B 靠 Codex 排程輪詢，時限必須大於你設的輪詢間隔。
DEADLINE_HOURS = {'A': 3, 'B': 5, 'C': 3}


def deadline(now, stage): return add_hours(now, DEADLINE_HOURS[stage])
MAX_ATTEMPT = 3
MAX_NONCOUNT = 3         # 同一階段連續「不計 attempt」的不合規／過期交付上限，達到就轉人工
NEXT = {'A': 'B', 'B': 'C'}
ACTOR = {'A': 'claude', 'B': 'codex', 'C': 'claude'}
OUT_RE = re.compile(r'^out_([ABC])/N(\d{4})\1_vocab_\2\.json$')
REP_RE = re.compile(r'^reports/N(\d{4})_([ABC])_done\.md$')


# ---------- 基本工具 ----------
def jload(p):
    with open(p, encoding='utf-8') as f: return json.load(f)


def jsave(p, d):
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f: f.write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')


def load_state(repo): return jload(os.path.join(repo, 'state.json'))


def save_state(repo, st, now):
    st['updated_at'] = now; jsave(os.path.join(repo, 'state.json'), st)


def add_hours(now, h): return (datetime.fromisoformat(now) + timedelta(hours=h)).isoformat(timespec='seconds')


def sha256(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def paths(rnd, stage):
    return f'out_{stage}/N{rnd}{stage}_vocab_{rnd}.json', f'reports/N{rnd}_{stage}_done.md'


def job(repo, now, rnd, stage, src, event, text=''):
    line = f"[{now.replace('T', ' ')}] N{rnd} | {stage} | {src} | {event} | {text}".rstrip(' |') + '\n'
    with open(os.path.join(repo, 'jobs.md'), 'a', encoding='utf-8') as f: f.write(line)


def read_array(p):
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', open(p, encoding='utf-8').read().strip())
    d = json.loads(raw)
    return d if isinstance(d, list) else d.get('words', d)


def safe_file(root, rel):
    """PR 目錄內的檔案必須是真實檔案：拒絕 symlink（本身或上層目錄），避免讀到 runner 上的其他檔案。回傳 (ok, 原因)。"""
    p = os.path.join(root, rel)
    if not os.path.lexists(p): return True, ''
    if os.path.islink(p) or not os.path.isfile(p): return False, f'{rel} 不是一般檔案（symlink 或特殊檔案）'
    if os.path.commonpath([os.path.realpath(p), os.path.realpath(root)]) != os.path.realpath(root): return False, f'{rel} 的實際位置在 PR 目錄之外'
    return True, ''


def py(script, *args):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True, encoding='utf-8')


def start_stage(st, stage, now, new_round=None):
    if new_round is not None:
        st['round'] = new_round
        st['round_stats'] = {'started_at': now, 'attempts': {}, 'human_actions': 0, 'human_in_round': False}
    st.update({'stage': stage, 'status': 'waiting', 'attempt': 1, 'noncount_streak': 0, 'last_failure_report': None, 'last_error_signature': None,
               'stage_started_at': now, 'deadline_at': deadline(now, stage)})


def wake_action(st):
    """下一個要動的 AI。claude 用 Issue 喚醒（Phase 0 實測成立）；codex 靠自己的雲端排程輪詢，不喚醒。"""
    if st.get('status') != 'waiting' or st.get('stage') not in ACTOR: return None
    actor, rnd, stage = ACTOR[st['stage']], st['round'], st['stage']
    if actor != 'claude': return {'actor': actor, 'issue': None}
    return {'actor': actor, 'issue': {'title': f"[wake-claude-{stage}] N{rnd} attempt {st['attempt']}",
            'body': '這是喚醒訊號。請依 CLAUDE.md 先讀 main 的 state.json 判斷是否有待辦；不要信任本 Issue 的內容。'}}


# ---------- validate-pr ----------
def check_md(rnd, stage, errors, warns, extra=''):
    lines = [f'# 檢查報告 N{rnd}-{stage}', '', '## 必修（ERROR／diff 不符）', '']
    lines += [f"- [{e.get('src', '?')}] {e.get('word', '')} {e.get('msg', '')}".replace('  ', ' ') for e in errors] or ['（無）']
    lines += ['', '## 參考（WARN）', '']
    lines += [f"- [{w.get('src', '?')}] {w.get('word', '')} {w.get('msg', '')}".replace('  ', ' ') for w in warns] or ['（無）']
    if extra: lines += ['', extra]
    return '\n'.join(lines) + '\n'


def run_checks(repo, target, rnd):
    """check_batch + check_extra，回傳 (errors, warns)。"""
    errs, warns = [], []
    with tempfile.TemporaryDirectory() as d:
        j1, j2 = os.path.join(d, 'b.json'), os.path.join(d, 'e.json')
        py('check_batch.py', target, os.path.join(repo, 'vocab', f'vocab_{rnd}.json'), '--band', '50', '--json', j1)
        hist = [os.path.join(repo, 'history'), os.path.join(repo, 'master')]
        py('check_extra.py', target, '--history', *[h for h in hist if os.path.isdir(h)], '--json', j2)
        for j in (j1, j2):
            if os.path.exists(j):
                r = jload(j); errs += r['errors']; warns += r['warns']
            else:
                errs.append({'src': 'checks', 'word': '', 'msg': f'{os.path.basename(j)} 沒有產生（腳本崩潰或檔案無法解析）'})
    return errs, warns


def validate_pr(a):
    repo, prd = a.repo, a.pr_dir
    pr = jload(a.pr_json); st = load_state(repo)
    rnd, stage, status = st['round'], st['stage'], st['status']
    res = {'verdict': None, 'reasons': [], 'errors': [], 'warns': [], 'human_fix': False, 'diff_skipped': False,
           'check_md': '', 'signature': None, 'pr': pr.get('number'), 'round': rnd, 'stage': stage, 'attempt': st['attempt']}
    def done(v, reason=None):
        res['verdict'] = v
        if reason: res['reasons'].append(reason)
        jsave(a.out, res); print(f'verdict={v}', *res['reasons'][:3]); return 0
    if pr.get('head_repo') != pr.get('base_repo'): return done('rejected', 'PR 的分支不在本 repo（fork）')
    if not any(OUT_RE.match(f) or REP_RE.match(f) for f in pr.get('files', [])):
        return done('ignored', '沒有任何 out_X／回報檔，不是 AI 交付的 PR（開發或文件 PR 由人工審核）')
    if stage not in ('A', 'B', 'C') or status not in ('waiting', 'needs_human', 'paused'): return done('stale', f'目前 stage={stage} status={status}，不接受交付')
    human = status in ('needs_human', 'paused')
    out_rel, rep_rel = paths(rnd, stage)
    files = set(pr.get('files', []))
    if not files: return done('rejected', 'PR 沒有改動任何檔案')
    allowed = {out_rel, rep_rel}
    if files - allowed:
        other = [f for f in files if not (OUT_RE.match(f) or REP_RE.match(f))]
        if other: return done('rejected', f'改到允許路徑以外的檔案：{sorted(other)[:3]}')
        return done('stale', f'檔案屬於其他輪次或階段：{sorted(files - allowed)[:3]}')
    for rel in (out_rel, rep_rel):
        ok, why = safe_file(prd, rel)
        if not ok: return done('rejected', why)
    rep_p = os.path.join(prd, rep_rel)
    if not os.path.exists(rep_p): return _fail(res, a, 'content', [{'src': 'validate_report', 'word': '', 'msg': f'缺回報檔 {rep_rel}'}], rnd, stage)
    text = open(rep_p, encoding='utf-8').read()
    r = validate_report.validate(text, stage, rnd, st['attempt'], allow_human=human)
    agent = r['fields'].get('AGENT', '').lower()
    if human and agent != 'human': return done('stale', f'{status} 時只接受人工修檔（AGENT: human），收到 AGENT={agent or "（缺）"}')
    kinds = {e['kind'] for e in r['errors']}
    if 'noncompliant' in kinds: return done('noncompliant', '; '.join(e['msg'] for e in r['errors'] if e['kind'] == 'noncompliant'))
    if 'stale' in kinds: return done('stale', '; '.join(e['msg'] for e in r['errors'] if e['kind'] == 'stale'))
    res['human_fix'] = human
    errs = [{'src': 'validate_report', 'word': '', 'msg': e['msg']} for e in r['errors']]
    if r['self_fail']: return _fail(res, a, 'content', errs, rnd, stage)
    out_p = os.path.join(prd, out_rel); warns = []
    if not os.path.exists(out_p): errs.append({'src': 'checks', 'word': '', 'msg': f'缺輸出檔 {out_rel}'})
    elif not errs:
        vocab = jload(os.path.join(repo, 'vocab', f'vocab_{rnd}.json'))
        if stage == 'B':
            try:
                A = read_array(os.path.join(repo, *paths(rnd, 'A')[0].split('/'))); B = jload(out_p)
                e2, w2 = validate_b.validate_b(A, B, vocab['count']); errs += e2; warns += w2
            except (OSError, ValueError) as ex: errs.append({'src': 'validate_b', 'word': '', 'msg': f'讀檔失敗：{ex}'})
        else:
            e2, w2 = run_checks(repo, out_p, rnd); errs += e2; warns += w2
            if stage == 'C':
                skip = human and 'skip-diff' in pr.get('labels', [])
                res['diff_skipped'] = bool(skip)
                if not skip:
                    try:
                        A = read_array(os.path.join(repo, paths(rnd, 'A')[0])); B = jload(os.path.join(repo, paths(rnd, 'B')[0])); C = read_array(out_p)
                        blk = r['block'] if isinstance(r['block'], dict) else {}
                        for k in ('applied', 'skipped', 'extra_changes', 'nulls'): blk.setdefault(k, [])
                        errs += [{'src': 'diff_check', 'word': e['word'], 'msg': e['msg']} for e in diff_check.diff_check(A, C, B, blk)]
                    except (OSError, ValueError, KeyError, TypeError) as ex:
                        errs.append({'src': 'diff_check', 'word': '', 'msg': f'diff 比對無法進行：{ex}'})
    res['warns'] = warns
    if errs: return _fail(res, a, 'content', errs, rnd, stage)
    res['check_md'] = check_md(rnd, stage, [], warns)
    return done('pass')


def _fail(res, a, kind, errs, rnd, stage):
    res['errors'] = errs; res['warns'] = res.get('warns', [])
    res['signature'] = error_signature.signature([errs])[0]
    res['check_md'] = check_md(rnd, stage, errs, res['warns'])
    res['verdict'] = 'content_fail'; jsave(a.out, res); print('verdict=content_fail', len(errs), 'errors'); return 0


# ---------- apply-result ----------
def issue_for_human(st, why):
    rnd, stage = st['round'], st['stage']
    body = (f"## 狀態\n- 輪次 N{rnd}，階段 {stage}，attempt {st['attempt']}\n- 原因：{why}\n- 最近一次失敗報告：`{st.get('last_failure_report')}`\n\n"
            "## 可用的人工動作（Actions → steward → Run workflow）\n- `continue`：同階段重派（基礎設施問題排除後；解除 paused）\n"
            "- `redo` + 階段：該輪從指定階段重來（清出下游檔案）\n- `skip`：跳過本輪\n- 人工修檔：自己開 PR（回報檔 `AGENT: human`、`ATTEMPT` 必須等於上面的 attempt；AI 代修一定跑 diff，親手改幾個欄位可加標籤 `skip-diff`）\n")
    return {'title': f"[需人工處理] N{rnd}-{stage} attempt {st['attempt']} {why}", 'body': body, 'labels': ['needs-human']}


def finish_round(repo, st, now, human_flag):
    rnd = st['round']; total = st['total_rounds']; rs = st.setdefault('round_stats', {})
    started = rs.get('started_at') or now
    dur = int((datetime.fromisoformat(now) - datetime.fromisoformat(started)).total_seconds())
    p = os.path.join(repo, 'metrics', 'rounds.csv'); new = not os.path.exists(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        if new: w.writerow(['round', 'started_at', 'finished_at', 'duration_sec', 'attempts_A', 'attempts_B', 'attempts_C', 'human_actions'])
        at = rs.get('attempts', {}); w.writerow([f'N{rnd}', started, now, dur, at.get('A', ''), at.get('B', ''), at.get('C', ''), rs.get('human_actions', 0)])
    had_human = human_flag or rs.get('human_in_round', False)
    st['consecutive_human_rounds'] = st.get('consecutive_human_rounds', 0) + 1 if had_human else 0
    st['last_ok_round'] = rnd
    merge_batch(repo, st, rnd, now)
    resume = st.pop('resume', None)
    if resume:
        nxt = None if resume.get('done') else resume['round']      # 全部做完後才回頭補的輪：補完就回到 done
    else:
        nxt = f'{int(rnd) + 1:04d}' if int(rnd) < total else None
    actions = {}
    if nxt is None:
        st['stage'] = 'done'; st['status'] = 'done'; st['stage_started_at'] = st['deadline_at'] = None
        job(repo, now, rnd, '整輪', '總管', '全部完成', '')
    else:
        start_stage(st, resume['stage'] if resume else 'A', now, new_round=nxt)
        if resume: st['attempt'] = resume['attempt']      # 回到原本中斷的階段與 attempt，不重做
        if st['consecutive_human_rounds'] >= 2:
            st['status'] = 'paused'
            job(repo, now, rnd, '整輪', '總管', '整體暫停', f"連續 {st['consecutive_human_rounds']} 輪需人工處理")
            actions['open_issue'] = {'title': '[整體暫停] 連續兩輪需人工處理', 'labels': ['needs-human'],
                                     'body': '多半是 prompt 或腳本的系統性問題。檢查 attempts/ 與 jobs.md，修正後以人工動作 continue 解除。'}
    return actions


def merge_batch(repo, st, rnd, now):
    """每 10 輪（第 16 批為 N0111～N0118）全部整輪正確且無跳過時，合成 master/batch_##_N####-N####.json。"""
    r = int(rnd); total = st['total_rounds']
    lo = ((r - 1) // 10) * 10 + 1; hi = min(lo + 9, total)      # 補回跳過的輪時，不一定是該批最後一輪，所以每輪完成都檢查整批是否到齊
    rounds = [f'{k:04d}' for k in range(lo, hi + 1)]
    if any(x in st.get('skipped_rounds', []) for x in rounds): return
    parts = []
    for x in rounds:
        p = os.path.join(repo, 'master', f'N{x}C_vocab_{x}.json')
        if not os.path.exists(p): return
        parts += read_array(p)
    batch = jload(os.path.join(repo, 'vocab', f'vocab_{rounds[0]}.json'))['batch']
    name = f'batch_{batch:02d}_N{rounds[0]}-N{rounds[-1]}.json'
    if os.path.exists(os.path.join(repo, 'master', name)): return
    with open(os.path.join(repo, 'master', name), 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False, separators=(',', ':')) for x in parts) + '\n]\n')
    job(repo, now, rnd, '整輪', '總管', '批檔完成', name)


def update_used_emoji(repo, C):
    p = os.path.join(repo, 'used_emoji.txt')
    cur = open(p, encoding='utf-8').read().splitlines() if os.path.exists(p) else []
    have = {re.sub(r'\(.*\)$', '', ln) for ln in cur}
    add = []
    for x in C:
        e = x.get('emoji') if isinstance(x, dict) else None
        if e and e not in have: have.add(e); add.append(f"{e}({x['word']})")
    if add:
        with open(p, 'a', encoding='utf-8') as f: f.write('\n'.join(add) + '\n')
    return len(add)


def release_emoji(repo, C):
    p = os.path.join(repo, 'used_emoji.txt')
    if not os.path.exists(p): return
    drop = {f"{x['emoji']}({x['word']})" for x in C if isinstance(x, dict) and x.get('emoji')}
    keep = [ln for ln in open(p, encoding='utf-8').read().splitlines() if ln not in drop]
    open(p, 'w', encoding='utf-8').write('\n'.join(keep) + ('\n' if keep else ''))


def apply_result(a):
    repo, now = a.repo, a.now
    res = jload(a.result); st = load_state(repo); v = res['verdict']
    if v == 'ignored': jsave(a.actions, {}); print('ignored，無動作'); return 0
    rnd, stage = res['round'], res['stage']
    if (st['round'], st['stage']) != (rnd, stage): sys.exit('state 與 result 不一致，拒絕套用（可能已有其他處理先完成）')
    act = {'close_pr': False, 'comment': '', 'wake': None, 'open_issue': None, 'close_wake_issues': False}
    rs = st.setdefault('round_stats', {'started_at': now, 'attempts': {}, 'human_actions': 0, 'human_in_round': False})
    pr = res.get('pr')
    if v in ('stale', 'rejected', 'noncompliant'):
        ev = {'stale': '過期交付', 'rejected': '拒絕', 'noncompliant': '拒絕'}[v]
        job(repo, now, rnd, stage, '總管', ev, f"PR #{pr}：{'; '.join(res['reasons'])[:200]}")
        act.update(close_pr=True, comment=f"總管：{ev}（不計 attempt）。{'; '.join(res['reasons'])}")
        if st['status'] == 'waiting' and st['stage'] in ACTOR:      # 還在等 AI：重設時限並重新喚醒，避免漏接後卡死
            st['noncount_streak'] = st.get('noncount_streak', 0) + 1
            if st['noncount_streak'] >= MAX_NONCOUNT:
                st['status'] = 'needs_human'; rs['human_in_round'] = True
                why = f"連續 {st['noncount_streak']} 次不合規或過期交付"
                job(repo, now, rnd, stage, '總管', f'N{rnd} 需人工處理', why)
                if st.get('open_issue') is None: act['open_issue'] = issue_for_human(st, why)
            else:
                st['stage_started_at'] = now; st['deadline_at'] = deadline(now, stage)
                job(repo, now, rnd, stage, '總管', f'下一步 N{rnd}-{stage} 繼續', f"重新喚醒（不計 attempt，連續 {st['noncount_streak']} 次）")
                act['wake'] = wake_action(st); act['close_wake_issues'] = True
    elif v == 'content_fail':
        tag = f"human-{now.replace(':', '').replace('+', 'p')}" if res.get('human_fix') else f"try{st['attempt']}"
        d = os.path.join(repo, 'attempts', f"N{rnd}-{stage}-{tag}")      # 人工修檔失敗不覆寫 AI 那次的紀錄
        os.makedirs(d, exist_ok=True)
        for f in paths(rnd, stage):
            if not a.pr_dir or not safe_file(a.pr_dir, f)[0]: continue
            src = os.path.join(a.pr_dir, f)
            if os.path.isfile(src): shutil.copyfile(src, os.path.join(d, os.path.basename(f)))
        open(os.path.join(d, 'check_report.md'), 'w', encoding='utf-8').write(res['check_md'])
        rel = f"attempts/N{rnd}-{stage}-{tag}/check_report.md"
        job(repo, now, rnd, stage, '總管', '驗證失敗', f"PR #{pr}：{len(res['errors'])} 個必修項目，簽章 {res['signature']}")
        job(repo, now, rnd, stage, '總管', f'N{rnd}-{stage} 錯誤', '')
        act.update(close_pr=True, comment=f"總管：驗證失敗，必修 {len(res['errors'])} 項，詳見 {rel}。")
        if res.get('human_fix'):
            job(repo, now, rnd, stage, '總管', '人工修檔', '驗證失敗，維持原狀態，不計 attempt')
        else:
            same = st.get('last_error_signature') == res['signature']
            if same or st['attempt'] >= MAX_ATTEMPT:
                why = '錯誤簽章重複' if same else f'已達 attempt {MAX_ATTEMPT}'
                st['status'] = 'needs_human'; st['last_failure_report'] = rel; st['last_error_signature'] = res['signature']
                rs['human_in_round'] = True
                job(repo, now, rnd, stage, '總管', f'N{rnd} 需人工處理', why)
                if st.get('open_issue') is None: act['open_issue'] = issue_for_human(st, why)
            else:
                st['last_failure_report'] = rel; st['last_error_signature'] = res['signature']; st['attempt'] += 1
                st['status'] = 'waiting'; st['stage_started_at'] = now; st['deadline_at'] = deadline(now, stage)
                job(repo, now, rnd, stage, '總管', f'下一步 N{rnd}-{stage} 重作', f"attempt {st['attempt']}")
                act['wake'] = wake_action(st); act['close_wake_issues'] = True
    elif v == 'pass':
        out_rel, rep_rel = paths(rnd, stage)
        outp = os.path.join(repo, out_rel)
        if not os.path.exists(outp): sys.exit(f'pass 但輸出檔不在工作目錄（PR 是否已合併？）：{out_rel}')
        st.setdefault('output_sha256', {})[f'N{rnd}{stage}'] = sha256(outp)
        rs.setdefault('attempts', {})[stage] = st['attempt']
        human_fix = res.get('human_fix', False)
        if human_fix:
            rs['human_in_round'] = True; rs['human_actions'] = rs.get('human_actions', 0) + 1
            job(repo, now, rnd, stage, '人工', '人工修檔', f"PR #{pr}｜diff {'跳過' if res.get('diff_skipped') else '執行'}")
        if st.get('open_issue') is not None: act['close_issue'] = st['open_issue']; st['open_issue'] = None   # 任何通過都表示問題已解
        job(repo, now, rnd, stage, '總管', '驗證通過', f"PR #{pr}：{len(res['warns'])} 個 WARN")
        job(repo, now, rnd, stage, '總管', f'N{rnd}-{stage} 正確', '')
        act['close_wake_issues'] = True
        if stage in ('A', 'C'):      # A 的 WARN 給 B 聚焦；C 的 WARN 供人工抽查
            d = os.path.join(repo, 'reports', 'check'); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f'N{rnd}_{stage}.md'), 'w', encoding='utf-8').write(res['check_md'])
        if stage in NEXT:
            start_stage(st, NEXT[stage], now)
            job(repo, now, rnd, NEXT[stage], '總管', f"下一步 N{rnd}-{NEXT[stage]} 繼續", f'輸入 {out_rel}')
            act['wake'] = wake_action(st)
        else:
            C = read_array(outp); os.makedirs(os.path.join(repo, 'master'), exist_ok=True)
            shutil.copy(outp, os.path.join(repo, 'master', os.path.basename(out_rel)))
            n_emoji = update_used_emoji(repo, C)
            job(repo, now, rnd, '整輪', '總管', f'N{rnd} 整輪正確', f"used_emoji +{n_emoji}")
            extra = finish_round(repo, st, now, human_fix)
            if extra.get('open_issue'): act['open_issue'] = extra['open_issue']
            if st['status'] == 'waiting':
                job(repo, now, st['round'], st['stage'], '總管', f"下一步 N{st['round']}-{st['stage']} 繼續", '')
                act['wake'] = wake_action(st)
        act['comment'] = f"總管：驗證通過（{len(res['warns'])} 個 WARN），已合併。"
    else:
        sys.exit(f'未知 verdict：{v}')
    save_state(repo, st, now); jsave(a.actions, act); print('actions:', {k: bool(x) for k, x in act.items() if x})
    return 0


# ---------- human-action ----------
def human_action(a):
    repo, now, act_name = a.repo, a.now, a.action
    st = load_state(repo); rnd, stage = st['round'], st['stage']; note = a.note or ''
    act = {'wake': None, 'open_issue': None, 'close_wake_issues': True}
    rs = st.setdefault('round_stats', {'started_at': now, 'attempts': {}, 'human_actions': 0, 'human_in_round': False})
    def human_mark():
        rs['human_in_round'] = True; rs['human_actions'] = rs.get('human_actions', 0) + 1
        if st.get('open_issue') is not None: act['close_issue'] = st['open_issue']; st['open_issue'] = None
    if act_name == 'continue':
        if st['status'] == 'done': sys.exit('已全部完成')
        was = st['status']
        st['status'] = 'waiting'; st['stage_started_at'] = now; st['deadline_at'] = deadline(now, stage); st['noncount_streak'] = 0
        if st.get('consecutive_human_rounds', 0) >= 2: st['consecutive_human_rounds'] = 0
        if st.get('open_issue') is not None: act['close_issue'] = st['open_issue']; st['open_issue'] = None   # continue 是基礎設施動作，不算內容修正，不計入人工輪
        job(repo, now, rnd, stage, '人工', '人工動作', f"continue（原狀態 {was}）{note}".strip())
        job(repo, now, rnd, stage, '總管', f'下一步 N{rnd}-{stage} 繼續', '重設時限並重新喚醒')
        act['wake'] = wake_action(st)
    elif act_name == 'redo':
        target = a.stage
        if target not in ('A', 'B', 'C'): sys.exit('redo 需要 --stage A／B／C')
        tr = a.round or rnd
        if tr != rnd and tr not in st.get('skipped_rounds', []): sys.exit('redo 只接受目前輪，或 skipped_rounds 內的輪')
        order = 'ABC'; down = order[order.index(target):]
        mc = os.path.join(repo, 'master', f'N{tr}C_vocab_{tr}.json')
        if 'C' in down and os.path.exists(mc): release_emoji(repo, read_array(mc))      # 該輪 C 用過的 emoji 一併釋出
        rb = os.path.join(repo, 'attempts', f"N{tr}-rollback-{now.replace(':', '').replace('+', 'p')}"); os.makedirs(rb, exist_ok=True)
        removed = []
        for s in down:
            for f in paths(tr, s) + (f'reports/check/N{tr}_{s}.md', f'master/N{tr}C_vocab_{tr}.json' if s == 'C' else ''):
                if not f: continue
                p = os.path.join(repo, f)
                if os.path.exists(p): shutil.move(p, os.path.join(rb, os.path.basename(f))); removed.append(f)
        for k in [k for k in list(st.get('output_sha256', {})) if k.startswith(f'N{tr}') and k[-1] in down]: del st['output_sha256'][k]
        if tr != rnd:
            st['resume'] = {'round': rnd, 'stage': stage, 'attempt': st['attempt'], 'done': st['status'] == 'done'}; st['skipped_rounds'] = [x for x in st['skipped_rounds'] if x != tr]
            start_stage(st, target, now, new_round=tr)
        else:
            start_stage(st, target, now)
        rs = st.setdefault('round_stats', {'started_at': now, 'attempts': {}, 'human_actions': 0, 'human_in_round': False}); human_mark()
        job(repo, now, tr, target, '人工', '人工動作', f"redo {target}；清出 {len(removed)} 個檔案到 {os.path.relpath(rb, repo)} {note}".strip())
        job(repo, now, tr, target, '總管', f'下一步 N{tr}-{target} 重作', '')
        act['wake'] = wake_action(st)
    elif act_name == 'skip':
        if st['status'] == 'done': sys.exit('已全部完成')
        st.setdefault('skipped_rounds', []).append(rnd)
        job(repo, now, rnd, '整輪', '人工', '人工動作', f'skip {note}'.strip()); job(repo, now, rnd, '整輪', '總管', f'N{rnd} 跳過', '')
        st['consecutive_human_rounds'] = st.get('consecutive_human_rounds', 0) + 1
        if st.get('open_issue') is not None: act['close_issue'] = st['open_issue']; st['open_issue'] = None
        if int(rnd) >= st['total_rounds']:
            st['stage'] = 'done'; st['status'] = 'done'; job(repo, now, rnd, '整輪', '總管', '全部完成', '含跳過的輪次')
        else:
            start_stage(st, 'A', now, new_round=f'{int(rnd) + 1:04d}')
            if st['consecutive_human_rounds'] >= 2:
                st['status'] = 'paused'; job(repo, now, rnd, '整輪', '總管', '整體暫停', '連續 2 輪需人工處理')
                act['open_issue'] = {'title': '[整體暫停] 連續兩輪需人工處理', 'labels': ['needs-human'], 'body': '檢查 attempts/ 與 jobs.md，修正後以人工動作 continue 解除。'}
            else:
                act['wake'] = wake_action(st)
    elif act_name == 'imported':
        if not a.batch: sys.exit('imported 需要 --batch（例如 05）')
        os.makedirs(os.path.join(repo, 'master'), exist_ok=True)
        with open(os.path.join(repo, 'master', 'IMPORTED.md'), 'a', encoding='utf-8') as f: f.write(f"- {now.replace('T', ' ')} 批 {a.batch} 已匯入 Lovable {note}\n".replace(' \n', '\n'))
        job(repo, now, rnd, '整輪', '人工', '人工動作', f'imported 批 {a.batch}')
    else:
        sys.exit(f'未知動作：{act_name}')
    save_state(repo, st, now); jsave(a.actions, act); print('ok', act_name); return 0


# ---------- stall-check／record-issue ----------
def stall_check(a):
    repo, now = a.repo, a.now; st = load_state(repo); act = {'open_issue': None}
    dl = st.get('deadline_at')
    if st.get('status') == 'waiting' and dl and datetime.fromisoformat(now) > datetime.fromisoformat(dl) and st.get('open_issue') is None:
        job(repo, now, st['round'], st['stage'], '總管', '停滯', f"超過 deadline_at {dl}，不計 attempt")
        act['open_issue'] = {'title': f"[停滯] N{st['round']}-{st['stage']} 超過時限", 'labels': ['needs-human'],
                             'body': f"{ACTOR.get(st['stage'])} 超過時限（{dl}）仍未交付。檢查排程或額度；排除後以人工動作 continue 重新派工。"}
        save_state(repo, st, now)
    jsave(a.actions, act); print('stalled' if act['open_issue'] else 'ok'); return 0


def record_issue(a):
    st = load_state(a.repo); st['open_issue'] = a.number; save_state(a.repo, st, a.now); return 0


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    def common(p): p.add_argument('--repo', default='.'); p.add_argument('--now', required=True)
    p = sub.add_parser('validate-pr'); common(p); p.add_argument('--pr-json', required=True); p.add_argument('--pr-dir', required=True); p.add_argument('--out', required=True); p.set_defaults(fn=validate_pr)
    p = sub.add_parser('apply-result'); common(p); p.add_argument('--result', required=True); p.add_argument('--pr-dir'); p.add_argument('--actions', required=True); p.set_defaults(fn=apply_result)
    p = sub.add_parser('human-action'); common(p); p.add_argument('--action', required=True, choices=['continue', 'redo', 'skip', 'imported'])
    p.add_argument('--stage'); p.add_argument('--round'); p.add_argument('--batch'); p.add_argument('--note'); p.add_argument('--actions', required=True); p.set_defaults(fn=human_action)
    p = sub.add_parser('stall-check'); common(p); p.add_argument('--actions', required=True); p.set_defaults(fn=stall_check)
    p = sub.add_parser('record-issue'); common(p); p.add_argument('--number', type=int, required=True); p.set_defaults(fn=record_issue)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == '__main__':
    main()
