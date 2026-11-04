#!/usr/bin/env python3
"""喚醒看門狗：總管推進到某階段之後，確認該階段真的有進展；沒有就補救或告警。
由 .github/workflows/wake_watchdog.yml 啟動（steward_finish.sh 在 wake 動作後 dispatch），每個「輪次＋階段＋attempt」一個。

每 INTERVAL 秒讀一次 main 的 state.json，依序判斷（decide）：
 1. state 已不是「這個輪次＋階段＋attempt 且 waiting」→ 已推進，關掉自己開過的 Issue 後結束（手動加速、B 階段都這樣自然結束）。
 2. 遠端已有這個階段的 open PR（分支 claude/N####-X 或 codex/N####-B，或標題 N#### X 開頭）→ AI 已交付，絕不重派；
    PR 開了 PR_GRACE 秒總管還沒處理（通常是 GitHub 5xx 讓總管失敗）→ 開一次 [總管卡住] Issue（needs-human），請人到 Actions 按 Re-run failed jobs。
 3. 沒有 PR、還沒等滿 WAIT 秒 → 繼續等。
 4. 沒有 PR、等滿了：分支 claude/N####-X 在 ACTIVE_WINDOW 秒內有新 commit → AI 還在做，繼續等。
 5. 否則（只有 claude 的 A／C）關舊喚醒 Issue、重開一個，最多 MAX_RETRIES 次；仍無動作開 [喚醒失敗] Issue（needs-human）。
    codex 的 B 不能被喚醒，只做第 2 點的偵測；B 的逾時由 stall_check 處理。
只開／關 Issue，不碰 state.json、不合併、不關 PR。腳本在 scripts/ 內，AI 不可改。"""
import argparse, datetime, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steward  # noqa: E402  只用 wake_action／ACTOR 取得與總管一致的標題與內文

WAIT = 900             # 秒：沒有任何動靜多久才認定沒被喚醒（A／C 平常 3～6 分鐘交付）
PR_GRACE = 600         # 秒：PR 開了多久總管還沒處理就告警（總管平常 1 分鐘內處理完）
ACTIVE_WINDOW = 1800   # 秒：分支最後一個 commit 在這段時間內就視為 AI 還在做
INTERVAL = 60
MAX_RETRIES = 3
CAP = {'A': 80 * 60, 'C': 80 * 60, 'B': 330 * 60}   # 秒：看門狗最長存活（B 靠 Codex 每小時輪詢，要看到 deadline 5 小時）


def matches(st, target):
    return (st is not None and st.get('status') == 'waiting' and st.get('stage') == target['stage']
            and st.get('round') == target['round'] and int(st.get('attempt', 0)) == int(target['attempt']))


def branch_for(target):
    return f"{steward.ACTOR[target['stage']]}/N{target['round']}-{target['stage']}"


def decide(st, target, waited, retries, active, pr, pr_age, alerted, wait=WAIT, max_retries=MAX_RETRIES, pr_grace=PR_GRACE):
    """回傳 done／wait／alert／rewake／giveup。pr 是這階段的 open PR（None 表示沒有），pr_age 是看到它多久了。"""
    if not matches(st, target): return 'done'
    if pr is not None:
        return 'alert' if (pr_age >= pr_grace and not alerted) else 'wait'
    if steward.ACTOR.get(target['stage']) != 'claude': return 'wait'      # B：不能喚醒 codex，只看 PR
    if waited < wait: return 'wait'
    if active: return 'wait'
    if retries >= max_retries: return 'giveup'
    return 'rewake'


def loop(ops, target, interval=INTERVAL, wait=WAIT, max_retries=MAX_RETRIES, total_cap=None, sleep=None, clock=None, log=print,
         pr_grace=PR_GRACE, active_window=ACTIVE_WINDOW):
    import time
    sleep = sleep or time.sleep; clock = clock or time.time
    total_cap = total_cap or CAP.get(target['stage'], 80 * 60)
    t0 = clock(); start = t0; retries = 0; errors = 0; pr_since = None; alerted = False
    while True:
        now = clock()
        if now - t0 > total_cap: log('看門狗達到存活上限，結束'); return 'timeout'
        try:
            st = ops.read_state()
            pr = ops.open_pr(target) if matches(st, target) else None
        except Exception as e:  # noqa: BLE001  網路暫時失敗不應讓看門狗死掉
            errors += 1; log(f'讀取失敗（{errors}）：{e}')
            if errors >= 10: return 'error'
            sleep(interval); continue
        errors = 0
        if pr is None: pr_since = None; alerted = False
        elif pr_since is None: pr_since = now; log(f'看到 PR #{pr}，等總管處理')
        waited = now - start
        active = (pr is None and matches(st, target) and waited >= wait
                  and steward.ACTOR.get(target['stage']) == 'claude' and ops.branch_active(target, now - active_window))
        d = decide(st, target, waited, retries, active, pr, (now - pr_since) if pr_since is not None else 0, alerted, wait, max_retries, pr_grace)
        if d == 'done':
            log('狀態已推進，看門狗結束'); ops.close_own_issues('狀態已推進，看門狗關閉。'); return 'done'
        if d == 'alert':
            alerted = True; log(f'PR #{pr} 開了 {int(now - pr_since)} 秒總管仍未處理，開 [總管卡住] Issue'); ops.alert_stuck(target, pr)
        elif d == 'rewake':
            retries += 1; log(f'{int(waited)} 秒沒有動作，重派喚醒（第 {retries} 次）'); ops.rewake(target, st, retries); start = clock()
        elif d == 'giveup':
            log('重派次數用完，開 [喚醒失敗] Issue'); ops.giveup(target, retries); return 'giveup'
        sleep(interval)


class GhOps:
    def __init__(self, repo): self.repo = repo; self.own_issues = []

    @staticmethod
    def sh(*args):
        r = subprocess.run(list(args), capture_output=True, text=True, encoding='utf-8')
        return r.returncode, r.stdout.strip()

    def read_state(self):
        rc, out = self.sh('git', 'fetch', '-q', 'origin', 'main')
        if rc != 0: raise RuntimeError('git fetch 失敗')
        rc, out = self.sh('git', 'show', 'FETCH_HEAD:state.json')
        if rc != 0: raise RuntimeError('讀不到 state.json')
        return json.loads(out)

    def open_pr(self, target):
        """這個階段的 open PR 編號（沒有則 None）。看分支名或標題，不看作者（PR 作者永遠是 repo 擁有者）。"""
        rc, out = self.sh('gh', 'pr', 'list', '--repo', self.repo, '--state', 'open', '--limit', '50', '--json', 'number,title,headRefName,isDraft')
        if rc != 0: raise RuntimeError('gh pr list 失敗')
        branch = branch_for(target); prefix = f"N{target['round']} {target['stage']} "
        for p in json.loads(out or '[]'):
            if p.get('isDraft'): continue
            if p.get('headRefName') == branch or (p.get('title') or '').startswith(prefix): return int(p['number'])
        return None

    def branch_active(self, target, since_epoch):
        rc, out = self.sh('gh', 'api', f'repos/{self.repo}/branches/{branch_for(target)}', '--jq', '.commit.commit.committer.date')
        if rc != 0 or not out: return False
        try: t = datetime.datetime.fromisoformat(out.replace('Z', '+00:00')).timestamp()
        except ValueError: return False
        return t >= since_epoch

    def _create(self, title, body, *labels, own=True):
        args = ['gh', 'issue', 'create', '--repo', self.repo, '--title', title, '--body', body]
        for l in labels: args += ['--label', l]
        for _ in range(3):
            rc, out = self.sh(*args)
            if rc == 0:
                n = out.rstrip('/').rsplit('/', 1)[-1]
                if own and n.isdigit(): self.own_issues.append(int(n))
                return out
            import time; time.sleep(10)
        print(f'警告：開 Issue 失敗：{title}', file=sys.stderr); return None

    def rewake(self, target, st, k):
        w = steward.wake_action(st)
        if not w or not w.get('issue'): return
        rc, out = self.sh('gh', 'issue', 'list', '--repo', self.repo, '--state', 'open', '--limit', '100', '--json', 'number,title',
                          '-q', '.[] | select(.title | startswith("[wake-claude")) | .number')
        for n in out.split():
            self.sh('gh', 'issue', 'close', n, '--repo', self.repo, '--comment', '看門狗：重新派工，關閉舊的喚醒訊號。')
        self._create(f"{w['issue']['title']} (重派 {k})", w['issue']['body'], own=False)   # 喚醒 Issue 由總管統一關

    def alert_stuck(self, target, pr):
        name = f"N{target['round']}-{target['stage']}"
        body = (f"{name} 的 PR #{pr} 已開 {PR_GRACE // 60} 分鐘以上，總管沒有處理（通常是 GitHub 回 5xx 讓總管的 workflow 失敗）。\n"
                f"處理方式：Actions → steward → 找到標題「N{target['round']} {target['stage']} 交付」且失敗（紅色）的那一筆 → Re-run failed jobs。\n"
                '若沒有失敗的執行，表示 PR 事件沒送到總管：在 PR 頁面按 Close 再 Reopen 即可重新觸發。看門狗不會重派喚醒。')
        self._create(f"[總管卡住] {name} PR #{pr}", body, 'needs-human')

    def giveup(self, target, retries):
        name = f"N{target['round']}-{target['stage']}"
        body = (f"{name} 已重派喚醒 {retries} 次，Claude 仍沒有動作（沒有分支、沒有 PR）。"
                '請檢查 claude.ai/code/routines 該任務的執行紀錄與設定，排除後用 steward 的人工動作 continue 重新派工。')
        self._create(f"[喚醒失敗] {name}", body, 'needs-human')

    def close_own_issues(self, comment):
        for n in self.own_issues:
            self.sh('gh', 'issue', 'close', str(n), '--repo', self.repo, '--comment', f'看門狗：{comment}')
        self.own_issues = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True); ap.add_argument('--round', required=True); ap.add_argument('--attempt', required=True)
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', ''))
    ap.add_argument('--interval', type=int, default=INTERVAL); ap.add_argument('--wait', type=int, default=WAIT)
    ap.add_argument('--max-retries', type=int, default=MAX_RETRIES); ap.add_argument('--total-cap', type=int, default=None)
    a = ap.parse_args()
    if not a.repo: print('需要 --repo 或 GITHUB_REPOSITORY', file=sys.stderr); sys.exit(2)
    if a.stage not in steward.ACTOR: print(f'未知階段：{a.stage}', file=sys.stderr); sys.exit(2)
    target = {'stage': a.stage, 'round': a.round, 'attempt': int(a.attempt)}
    r = loop(GhOps(a.repo), target, a.interval, a.wait, a.max_retries, a.total_cap)
    print(f'看門狗結果：{r}')


if __name__ == '__main__':
    main()
