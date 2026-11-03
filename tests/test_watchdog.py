"""喚醒看門狗（scripts/wake_watchdog.py）的測試：決策表、迴圈（假時鐘）、與 workflow／收尾腳本的接線。"""
import os, re, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import wake_watchdog as W  # noqa: E402

T = {'stage': 'A', 'round': '0033', 'attempt': 1}
ST = {'stage': 'A', 'round': '0033', 'attempt': 1, 'status': 'waiting'}


class FakeOps:
    def __init__(self, states, active=False, clock=None):
        self.states = list(states); self.active = active; self.clock = clock; self.rewakes = []; self.giveups = []; self.active_calls = []
    def read_state(self):
        s = self.states[0] if len(self.states) == 1 else self.states.pop(0)
        if isinstance(s, Exception): raise s
        return s
    def is_active(self, target, since): self.active_calls.append(since); return self.active
    def rewake(self, target, st, k): self.rewakes.append(k)
    def giveup(self, target, retries): self.giveups.append(retries)


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t
    def sleep(self, s): self.t += s


def run_loop(ops, **kw):
    c = Clock(); logs = []
    r = W.loop(ops, T, interval=60, wait=900, max_retries=3, sleep=c.sleep, clock=c, log=logs.append, **kw)
    return r, c, logs


class Decide(unittest.TestCase):
    def test_done_when_state_moved_on(self):
        for st in ({**ST, 'stage': 'B'}, {**ST, 'round': '0034'}, {**ST, 'attempt': 2}, {**ST, 'status': 'validating'}, {**ST, 'status': 'needs_human'}, None):
            self.assertEqual(W.decide(st, T, 5000, 0, False), 'done')
    def test_wait_until_threshold(self):
        self.assertEqual(W.decide(ST, T, 899, 0, False), 'wait')
        self.assertEqual(W.decide(ST, T, 900, 0, False), 'rewake')
    def test_active_branch_extends_wait_once(self):
        self.assertEqual(W.decide(ST, T, 1000, 0, True), 'wait')
        self.assertEqual(W.decide(ST, T, 1800, 0, True), 'rewake')   # 活著也不能無限等
    def test_giveup_after_max_retries(self):
        self.assertEqual(W.decide(ST, T, 900, 2, False), 'rewake')
        self.assertEqual(W.decide(ST, T, 900, 3, False), 'giveup')
    def test_b_stage_target_never_matches_other_stage(self):
        self.assertEqual(W.decide({**ST, 'stage': 'B'}, T, 5000, 0, False), 'done')   # 手動加速進到 B 時，A 的看門狗直接結束


class Loop(unittest.TestCase):
    def test_exits_immediately_when_progressed(self):
        ops = FakeOps([{**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, []); self.assertEqual(c.t, 1000.0)
    def test_exits_when_claude_delivers_in_time(self):
        ops = FakeOps([ST] * 5 + [{**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, []); self.assertEqual(ops.giveups, [])
    def test_rewake_then_success(self):
        ops = FakeOps([ST] * 16 + [{**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, [1])
    def test_rewake_three_times_then_giveup(self):
        ops = FakeOps([ST]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'giveup'); self.assertEqual(ops.rewakes, [1, 2, 3]); self.assertEqual(ops.giveups, [3])
        self.assertLess(c.t - 1000.0, W.TOTAL_CAP)    # 在存活上限內結束
    def test_active_branch_prevents_duplicate_wake(self):
        ops = FakeOps([ST] * 20 + [{**ST, 'stage': 'B'}], active=True); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done'); self.assertEqual(ops.rewakes, [])
    def test_transient_read_errors_do_not_kill(self):
        ops = FakeOps([RuntimeError('x'), RuntimeError('x'), {**ST, 'stage': 'B'}]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'done')
    def test_persistent_read_errors_stop(self):
        ops = FakeOps([RuntimeError('x')]); r, c, _ = run_loop(ops)
        self.assertEqual(r, 'error')
    def test_total_cap(self):
        ops = FakeOps([ST], active=True); c = Clock(); logs = []
        r = W.loop(ops, T, interval=60, wait=10**9, max_retries=3, total_cap=600, sleep=c.sleep, clock=c, log=logs.append)
        self.assertEqual(r, 'timeout')


class Wiring(unittest.TestCase):
    def test_finish_script_dispatches_watchdog_only_with_wake(self):
        s = open(os.path.join(ROOT, 'scripts', 'steward_finish.sh'), encoding='utf-8').read()
        self.assertIn('gh workflow run wake_watchdog.yml', s)
        m = re.search(r'if \[ "\$\(jqr \'\.wake\.issue != null\'\)" = "true" \]; then(.*?)\nfi', s, re.S)
        self.assertTrue(m and 'gh workflow run wake_watchdog.yml' in m.group(1))      # 只在有喚醒 Issue 時才啟動
        self.assertIn('|| echo', m.group(1))                                           # 失敗不能讓收尾腳本中止（set -e）
        self.assertEqual(subprocess.run(['bash', '-n', os.path.join(ROOT, 'scripts', 'steward_finish.sh')]).returncode, 0)
    def test_workflow_shape(self):
        try: import yaml
        except ImportError: self.skipTest('需要 PyYAML')
        d = yaml.safe_load(open(os.path.join(ROOT, '.github', 'workflows', 'wake_watchdog.yml'), encoding='utf-8'))
        on = d.get('on') or d.get(True)
        self.assertEqual(set(on['workflow_dispatch']['inputs']), {'stage', 'round', 'attempt'})
        self.assertNotEqual(d['concurrency']['group'], 'steward')                      # 不可卡住總管
        self.assertNotIn('contents: write', str(d['permissions']))
        self.assertNotEqual(d['permissions'].get('contents'), 'write')
        for f in ('steward.yml', 'stall_check.yml'):
            w = yaml.safe_load(open(os.path.join(ROOT, '.github', 'workflows', f), encoding='utf-8'))
            self.assertEqual(w['permissions'].get('actions'), 'write')                 # gh workflow run 需要
    def test_titles_match_routine_filter(self):
        import steward
        w = steward.wake_action({'status': 'waiting', 'stage': 'A', 'round': '0033', 'attempt': 1})
        t = f"{w['issue']['title']} (重派 1)"
        self.assertIn('[wake-claude-A]', t); self.assertTrue(t.startswith('[wake-claude'))   # 舊 Issue 的關閉規則與 routine 的「包含」篩選都仍成立
        self.assertIsNone(steward.wake_action({'status': 'waiting', 'stage': 'B', 'round': '0033', 'attempt': 1})['issue'])


if __name__ == '__main__':
    unittest.main()
