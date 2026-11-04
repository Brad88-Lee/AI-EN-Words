"""喚醒看門狗（scripts/wake_watchdog.py）的測試：決策表、迴圈（假時鐘）、與 workflow／收尾腳本的接線。"""
import os, re, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import wake_watchdog as W  # noqa: E402

T = {'stage': 'A', 'round': '0033', 'attempt': 1}
ST = {'stage': 'A', 'round': '0033', 'attempt': 1, 'status': 'waiting'}
TB = {'stage': 'B', 'round': '0046', 'attempt': 1}
STB = {'stage': 'B', 'round': '0046', 'attempt': 1, 'status': 'waiting'}


class FakeOps:
    """states：每次 read_state 取下一個（最後一個重複）。prs：同樣規則，給 open_pr 用。active：branch_active 的回傳。"""
    def __init__(self, states, active=False, prs=(None,), fail_pr=False):
        self.states = list(states); self.prs = list(prs); self.active = active; self.fail_pr = fail_pr
        self.rewakes = []; self.giveups = []; self.alerts = []; self.closed = 0; self.active_calls = 0
    def _next(self, seq):
        s = seq[0] if len(seq) == 1 else seq.pop(0)
        if isinstance(s, Exception): raise s
        return s
    def read_state(self): return self._next(self.states)
    def open_pr(self, target):
        if self.fail_pr: raise RuntimeError('gh pr list 失敗')
        return self._next(self.prs)
    def branch_active(self, target, since): self.active_calls += 1; return self.active
    def rewake(self, target, st, k): self.rewakes.append(k)
    def giveup(self, target, retries): self.giveups.append(retries)
    def alert_stuck(self, target, pr): self.alerts.append(pr)
    def close_own_issues(self, comment): self.closed += 1


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t
    def sleep(self, s): self.t += s


def run_loop(ops, target=T, **kw):
    c = Clock(); logs = []
    kw.setdefault('total_cap', 80 * 60)
    r = W.loop(ops, target, interval=60, wait=900, max_retries=3, sleep=c.sleep, clock=c, log=logs.append, pr_grace=600, **kw)
    return r, c, logs


class Decide(unittest.TestCase):
    def d(self, st, waited, retries=0, active=False, pr=None, pr_age=0, alerted=False, target=T):
        return W.decide(st, target, waited, retries, active, pr, pr_age, alerted, wait=900, max_retries=3, pr_grace=600)
    def test_done_when_state_moved_on(self):
        for st in ({**ST, 'stage': 'B'}, {**ST, 'round': '0034'}, {**ST, 'attempt': 2}, {**ST, 'status': 'validating'}, {**ST, 'status': 'needs_human'}, None):
            self.assertEqual(self.d(st, 5000), 'done')
    def test_wait_until_threshold_then_rewake(self):
        self.assertEqual(self.d(ST, 899), 'wait'); self.assertEqual(self.d(ST, 900), 'rewake')
    def test_active_branch_waits(self):
        self.assertEqual(self.d(ST, 3000, active=True), 'wait')
    def test_giveup_after_max_retries(self):
        self.assertEqual(self.d(ST, 900, retries=2), 'rewake'); self.assertEqual(self.d(ST, 900, retries=3), 'giveup')
    def test_open_pr_never_rewakes(self):
        """N0068-C 的教訓：PR 已交付、總管因 GitHub 5xx 沒處理，看門狗不可重派。"""
        self.assertEqual(self.d(ST, 5000, pr=388, pr_age=0), 'wait')
        self.assertEqual(self.d(ST, 5000, retries=3, pr=388, pr_age=0), 'wait')
    def test_open_pr_alerts_once_after_grace(self):
        self.assertEqual(self.d(ST, 5000, pr=388, pr_age=599), 'wait')
        self.assertEqual(self.d(ST, 5000, pr=388, pr_age=600), 'alert')
        self.assertEqual(self.d(ST, 5000, pr=388, pr_age=6000, alerted=True), 'wait')
    def test_stage_b_only_watches_pr(self):
        self.assertEqual(self.d(STB, 10 ** 6, target=TB), 'wait')                       # 永不 rewake／giveup
        self.assertEqual(self.d(STB, 10 ** 6, pr=268, pr_age=600, target=TB), 'alert')  # N0046-B 的情境
        self.assertEqual(self.d({**STB, 'stage': 'C'}, 0, target=TB), 'done')


class Loop(unittest.TestCase):
    def test_exits_immediately_when_progressed(self):
        ops = FakeOps([{**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, []); self.assertEqual(c.t, 1000.0); self.assertEqual(ops.closed, 1)
    def test_exits_when_claude_delivers_in_time(self):
        ops = FakeOps([ST] * 5 + [{**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, []); self.assertEqual(ops.alerts, [])
    def test_rewake_then_success(self):
        ops = FakeOps([ST] * 16 + [{**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, [1])
    def test_rewake_three_times_then_giveup(self):
        ops = FakeOps([ST]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'giveup'); self.assertEqual(ops.rewakes, [1, 2, 3]); self.assertEqual(ops.giveups, [3])
        self.assertLess(c.t - 1000.0, 80 * 60)
    def test_active_branch_prevents_duplicate_wake(self):
        ops = FakeOps([ST] * 20 + [{**ST, 'stage': 'B'}], active=True); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, []); self.assertGreater(ops.active_calls, 0)
    def test_pr_pending_alerts_once_and_never_rewakes(self):
        """PR 一直開著、總管沒處理：等 10 分鐘開一次 [總管卡住]，之後一直等到存活上限，絕不重派。"""
        ops = FakeOps([ST], prs=[388]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'timeout'); self.assertEqual(ops.alerts, [388]); self.assertEqual(ops.rewakes, []); self.assertEqual(ops.giveups, [])
    def test_pr_pending_then_steward_recovers(self):
        ops = FakeOps([ST] * 15 + [{**ST, 'stage': 'B'}], prs=[388]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.alerts, [388]); self.assertEqual(ops.closed, 1)   # 自己開的 Issue 自己關
    def test_pr_appears_late_blocks_rewake_from_then_on(self):
        """前 20 分鐘沒 PR（重派 1 次），之後 PR 出現 → 不再重派。"""
        ops = FakeOps([ST], prs=[None] * 20 + [388]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'timeout'); self.assertEqual(ops.rewakes, [1]); self.assertEqual(ops.alerts, [388])
    def test_pr_closed_by_steward_as_stale_resets(self):
        """PR 被總管判過期關掉（state 不變、attempt 不變），看門狗回到沒有 PR 的邏輯。"""
        ops = FakeOps([ST], prs=[388] * 5 + [None]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'giveup'); self.assertEqual(ops.alerts, []); self.assertEqual(ops.rewakes, [1, 2, 3])
    def test_stage_b_pr_pending_alert(self):
        ops = FakeOps([STB] * 15 + [{**STB, 'stage': 'C'}], prs=[268]); r, c, _ = run_loop(ops, target=TB)
        self.assertEqual(r, 'done'); self.assertEqual(ops.alerts, [268]); self.assertEqual(ops.rewakes, [])
    def test_stage_b_no_pr_waits_until_cap_without_rewake(self):
        ops = FakeOps([STB]); r, c, _ = run_loop(ops, target=TB, total_cap=W.CAP['B'])
        self.assertEqual(r, 'timeout'); self.assertEqual(ops.rewakes, []); self.assertEqual(ops.giveups, []); self.assertEqual(ops.active_calls, 0)
        self.assertGreaterEqual(c.t - 1000.0, 5 * 3600)   # B 的存活上限要超過 deadline 5 小時
    def test_transient_read_errors_do_not_kill(self):
        ops = FakeOps([RuntimeError('x'), RuntimeError('x'), {**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done')
    def test_pr_list_errors_do_not_kill(self):
        ops = FakeOps([ST] * 3 + [{**ST, 'stage': 'B'}], fail_pr=True); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done')
    def test_persistent_read_errors_stop(self):
        ops = FakeOps([RuntimeError('x')]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'error')


class Wiring(unittest.TestCase):
    def test_finish_script_dispatches_watchdog_for_every_wake(self):
        s = open(os.path.join(ROOT, 'scripts', 'steward_finish.sh'), encoding='utf-8').read()
        m = re.search(r'if \[ "\$\(jqr \'\.wake != null\'\)" = "true" \]; then(.*?)\nfi', s, re.S)
        self.assertTrue(m, '看門狗要在 wake != null（含 codex 的 B）時啟動')
        blk = m.group(1)
        self.assertIn('gh workflow run wake_watchdog.yml', blk)
        self.assertIn("jqr '.wake.issue != null'", blk)                                  # 喚醒 Issue 只給 claude
        self.assertIn('gh_retry.sh', s); self.assertIn('"$RETRY" 4 gh issue create', blk)
        self.assertNotRegex(blk, r'gh issue create[^\n]*\n(?![^\n]*\|\|)')               # 喚醒 Issue 失敗不可中止（state 已推上 main）
        self.assertIn('[喚醒失敗]', s); self.assertIn('[總管卡住]', s)                     # 階段推進時一併關看門狗的 Issue
        self.assertEqual(subprocess.run(['bash', '-n', os.path.join(ROOT, 'scripts', 'steward_finish.sh')]).returncode, 0)
    def test_workflow_shape(self):
        try: import yaml
        except ImportError: self.skipTest('需要 PyYAML')
        d = yaml.safe_load(open(os.path.join(ROOT, '.github', 'workflows', 'wake_watchdog.yml'), encoding='utf-8'))
        on = d.get('on') or d.get(True)
        self.assertEqual(set(on['workflow_dispatch']['inputs']), {'stage', 'round', 'attempt'})
        self.assertNotEqual(d['concurrency']['group'], 'steward')
        self.assertNotEqual(d['permissions'].get('contents'), 'write')
        self.assertEqual(d['permissions'].get('pull-requests'), 'read')                   # gh pr list 需要
        self.assertGreaterEqual(d['jobs']['watch']['timeout-minutes'] * 60, W.CAP['B'])
        for f in ('steward.yml', 'stall_check.yml'):
            w = yaml.safe_load(open(os.path.join(ROOT, '.github', 'workflows', f), encoding='utf-8'))
            self.assertEqual(w['permissions'].get('actions'), 'write')
    def test_titles_match_routine_filter(self):
        import steward
        w = steward.wake_action({'status': 'waiting', 'stage': 'A', 'round': '0033', 'attempt': 1})
        t = f"{w['issue']['title']} (重派 1)"
        self.assertIn('[wake-claude-A]', t); self.assertTrue(t.startswith('[wake-claude'))
        self.assertIsNone(steward.wake_action({'status': 'waiting', 'stage': 'B', 'round': '0033', 'attempt': 1})['issue'])
        self.assertEqual(W.branch_for(TB), 'codex/N0046-B'); self.assertEqual(W.branch_for(T), 'claude/N0033-A')
    def test_gh_ops_open_pr_matching(self):
        """open_pr：看分支名或標題前綴，略過 draft。用假 sh 餵資料。"""
        import json
        ops = W.GhOps('o/r')
        data = [{'number': 5, 'title': 'N0033 A 交付', 'headRefName': 'claude/N0033-A', 'isDraft': False},
                {'number': 6, 'title': 'N0046 B 校正交付', 'headRefName': 'codex/N0046-B', 'isDraft': False},
                {'number': 7, 'title': 'N0047 A 交付', 'headRefName': 'x', 'isDraft': True},
                {'number': 8, 'title': '加入看門狗', 'headRefName': 'claude/nice-noether', 'isDraft': False}]
        ops.sh = staticmethod(lambda *a: (0, json.dumps(data)))
        self.assertEqual(ops.open_pr(T), 5); self.assertEqual(ops.open_pr(TB), 6)
        self.assertIsNone(ops.open_pr({'stage': 'A', 'round': '0047', 'attempt': 1}))     # draft 不算
        self.assertIsNone(ops.open_pr({'stage': 'C', 'round': '0033', 'attempt': 1}))


if __name__ == '__main__':
    unittest.main()
