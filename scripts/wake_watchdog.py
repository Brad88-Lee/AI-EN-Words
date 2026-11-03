#!/usr/bin/env python3
"""喚醒看門狗：總管開出 [wake-claude-X] Issue 之後，確認 Claude 真的有動作；沒有就重開喚醒 Issue。
由 .github/workflows/wake_watchdog.yml 啟動（steward_finish.sh 開完喚醒 Issue 後 dispatch），每個「輪次＋階段＋attempt」一個。

規則（decide）：
 1. main 的 state.json 已不是「這個輪次＋階段＋attempt 且 waiting」→ 工作已推進，看門狗結束（B 階段或手動加速時也是這樣自然結束）。
 2. 還沒等滿 WAIT 秒 → 繼續等。
 3. 等滿後，若遠端已有「喚醒之後才更新」的 claude/N####-X 分支 → 視為 Claude 正在做，繼續等（最多再等一個 WAIT，避免無限等）。
 4. 否則重開喚醒 Issue（先關舊的），最多 MAX_RETRIES 次；仍沒動作就開 [喚醒失敗] Issue（needs-human）後結束。
只開／關 Issue，不碰 state.json、不合併、不關 PR。腳本在 scripts/ 內，AI 不可改。"""
import argparse, datetime, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steward  # noqa: E402  只用 wake_action 取得與總管一致的標題與內文

WAIT = 900          # 秒：等多久才認定沒被喚醒（A 平常約 3～6 分鐘）
INTERVAL = 60
MAX_RETRIES = 3
TOTAL_CAP = 80 * 60  # 秒：看門狗最長存活時間（workflow timeout 為 90 分）


def matches(st, target):
    return (st is not None and st.get('status') == 'waiting' and st.get('stage') == target['stage']
            and st.get('round') == target['round'] and int(st.get('attempt', 0)) == int(target['attempt']))


def decide(st, target, waited, retries, active, wait=WAIT, max_retries=MAX_RETRIES):
    """回傳 done／wait／rewake／giveup。"""
    if not matches(st, target): return 'done'
    if waited < wait: return 'wait'
    if active and waited < wait * 2: return 'wait'
    if retries >= max_retries: return 'giveup'
    return 'rewake'


def loop(ops, target, interval=INTERVAL, wait=WAIT, max_retries=MAX_RETRIES, total_cap=TOTAL_CAP, sleep=None, clock=None, log=print):
    import time
    sleep = sleep or time.sleep; clock = clock or time.time
    t0 = clock(); start = t0; retries = 0; errors = 0
    while True:
        if clock() - t0 > total_cap: log('看門狗達到存活上限，結束'); return 'timeout'
        try: st = ops.read_state()
        except Exception as e:  # noqa: BLE001  網路暫時失敗不應讓看門狗死掉
            errors += 1; log(f'讀取 state 失敗（{errors}）：{e}')
            if errors >= 10: return 'error'
            sleep(interval); continue
        errors = 0
        waited = clock() - start
        active = ops.is_active(target, start - 60) if (matches(st, target) and waited >= wait) else False
        d = decide(st, target, waited, retries, active, wait, max_retries)
        if d == 'done': log('狀態已推進，看門狗結束'); return 'done'
        if d == 'rewake':
            retries += 1; log(f'{int(waited)} 秒沒有動作，重派喚醒（第 {retries} 次）'); ops.rewake(target, st, retries); start = clock()
        elif d == 'giveup':
            log('重派次數用完，開人工處理 Issue'); ops.giveup(target, retries); return 'giveup'
        else: sleep(interval)


class GhOps:
    def __init__(self, repo): self.repo = repo

    @staticmethod
    def sh(*args):
        r = subprocess.run(list(args), capture_output=True, text=True, encoding='utf-8')
        return r.returncode, r.stdout.strip()

    def read_state(self):
        rc, out = self.sh('git', 'fetch', '-q', 'origin', 'main')
        if rc != 0: raise RuntimeError('git fetch 失敗')
        rc, out = self.sh('git', 'show', 'FETCH_HEAD:state.json')
        if rc != 0: raise RuntimeError('讀不到 state.json')
        import json
        return json.loads(out)

    def is_active(self, target, since_epoch):
        branch = f"claude/N{target['round']}-{target['stage']}"
        rc, out = self.sh('gh', 'api', f'repos/{self.repo}/branches/{branch}', '--jq', '.commit.commit.committer.date')
        if rc != 0 or not out: return False
        try: t = datetime.datetime.fromisoformat(out.replace('Z', '+00:00')).timestamp()
        except ValueError: return False
        return t >= since_epoch

    def rewake(self, target, st, k):
        w = steward.wake_action(st)
        if not w or not w.get('issue'): return
        rc, out = self.sh('gh', 'issue', 'list', '--repo', self.repo, '--state', 'open', '--limit', '100', '--json', 'number,title',
                          '-q', '.[] | select(.title | startswith("[wake-claude")) | .number')
        for n in out.split():
            self.sh('gh', 'issue', 'close', n, '--repo', self.repo, '--comment', '看門狗：重新派工，關閉舊的喚醒訊號。')
        self.sh('gh', 'issue', 'create', '--repo', self.repo, '--title', f"{w['issue']['title']} (重派 {k})", '--body', w['issue']['body'])

    def giveup(self, target, retries):
        body = (f"N{target['round']}-{target['stage']} 已重派喚醒 {retries} 次，Claude 仍沒有動作。"
                '請檢查 claude.ai/code/routines 該任務的執行紀錄與設定，排除後用 steward 的人工動作 continue 重新派工。')
        self.sh('gh', 'issue', 'create', '--repo', self.repo, '--title', f"[喚醒失敗] N{target['round']}-{target['stage']}", '--body', body, '--label', 'needs-human')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True); ap.add_argument('--round', required=True); ap.add_argument('--attempt', required=True)
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', ''))
    ap.add_argument('--interval', type=int, default=INTERVAL); ap.add_argument('--wait', type=int, default=WAIT)
    ap.add_argument('--max-retries', type=int, default=MAX_RETRIES)
    a = ap.parse_args()
    if not a.repo: print('需要 --repo 或 GITHUB_REPOSITORY', file=sys.stderr); sys.exit(2)
    target = {'stage': a.stage, 'round': a.round, 'attempt': int(a.attempt)}
    r = loop(GhOps(a.repo), target, a.interval, a.wait, a.max_retries)
    print(f'看門狗結果：{r}')


if __name__ == '__main__':
    main()
