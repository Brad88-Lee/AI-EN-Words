"""總管 steward.py 的情境測試：在暫存 repo 裡模擬完整一輪與各種失敗、人工動作。
用 tests/fixtures/real 的真實資料（Final 當作乾淨的 A／C，A_0410 當作有 ERROR 的 A）。"""
import json, os, shutil, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import diff_check, validate_b, validate_report  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEWARD = os.path.join(ROOT, 'scripts', 'steward.py')
REAL = os.path.join(ROOT, 'tests', 'fixtures', 'real')
NOW = '2026-11-01T10:00:00+08:00'


def jl(name): return json.load(open(os.path.join(REAL, name), encoding='utf-8'))


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', script), *args], capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout + r.stderr


def wj(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False)


class Env:
    """repo（main 工作目錄）＋ pr 目錄（PR head 的檔案）。total_rounds=2：N0001 用 Final_0409 的字，N0002 用 Final_0410 的字。"""
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(); self.repo = os.path.join(self.tmp.name, 'repo'); self.pr = os.path.join(self.tmp.name, 'pr')
        os.makedirs(self.repo); os.makedirs(self.pr)
        for k, f in (('0001', 'Final_0409.json'), ('0002', 'Final_0410.json')):
            words = [x['word'] for x in jl(f)]
            wj(os.path.join(self.repo, 'vocab', f'vocab_{k}.json'), {'round': k, 'batch': 5, 'seq_from': 1, 'seq_to': len(words), 'count': len(words), 'words': [{'seq': i + 1, 'word': w} for i, w in enumerate(words)]})
        for d in ('history', 'master', 'attempts', 'reports/check', 'out_A', 'out_B', 'out_C', 'metrics'): os.makedirs(os.path.join(self.repo, d), exist_ok=True)
        open(os.path.join(self.repo, 'jobs.md'), 'w').write('# jobs\n'); open(os.path.join(self.repo, 'used_emoji.txt'), 'w').write('')
        self.set_state({'schema_version': 1, 'round': '0001', 'total_rounds': 2, 'stage': 'A', 'status': 'waiting', 'attempt': 1, 'last_failure_report': None,
                        'last_error_signature': None, 'stage_started_at': NOW, 'deadline_at': '2026-11-01T13:00:00+08:00', 'last_ok_round': None, 'skipped_rounds': [],
                        'consecutive_human_rounds': 0, 'output_sha256': {}, 'open_issue': None, 'updated_at': NOW})
    def close(self): self.tmp.cleanup()
    def state(self): return json.load(open(os.path.join(self.repo, 'state.json'), encoding='utf-8'))
    def set_state(self, st): wj(os.path.join(self.repo, 'state.json'), st)
    def jobs(self): return open(os.path.join(self.repo, 'jobs.md'), encoding='utf-8').read()
    def steward(self, *args):
        r = subprocess.run([sys.executable, STEWARD, *args, '--repo', self.repo, '--now', NOW], capture_output=True, text=True, encoding='utf-8')
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout
    def report(self, stage, rnd, attempt, agent, gate='PASS｜x', block=None, out=True):
        t = f"ROUND: N{rnd}\nSTAGE: {stage}\nAGENT: {agent}\nATTEMPT: {attempt}\nOUTPUT: out_{stage}/N{rnd}{stage}_vocab_{rnd}.json\nGATE-{stage}: {gate}\nMODEL: unknown\n---\n"
        if block is not None: t += '```json\n' + json.dumps(block) + '\n```\n---\n'
        return t
    def deliver(self, stage, rnd, data, attempt=1, agent=None, labels=(), extra_files=(), report_text=None, head_repo='o/r'):
        """把 PR 的檔案寫進 pr 目錄，回傳 validate-pr 的 result。"""
        shutil.rmtree(self.pr); os.makedirs(self.pr)
        agent = agent or {'A': 'claude', 'B': 'codex', 'C': 'claude'}[stage]
        out_rel, rep_rel = f'out_{stage}/N{rnd}{stage}_vocab_{rnd}.json', f'reports/N{rnd}_{stage}_done.md'
        wj(os.path.join(self.pr, out_rel), data)
        blk = {'a_count': 50, 'c_count': 50, 'applied': [], 'skipped': [], 'extra_changes': [], 'nulls': []} if stage == 'C' else None
        os.makedirs(os.path.join(self.pr, 'reports'), exist_ok=True)
        open(os.path.join(self.pr, rep_rel), 'w', encoding='utf-8').write(report_text or self.report(stage, rnd, attempt, agent, block=blk))
        files = [out_rel, rep_rel] + list(extra_files)
        wj(os.path.join(self.tmp.name, 'pr.json'), {'number': 7, 'head_repo': head_repo, 'base_repo': 'o/r', 'labels': list(labels), 'files': files})
        self.steward('validate-pr', '--pr-json', os.path.join(self.tmp.name, 'pr.json'), '--pr-dir', self.pr, '--out', os.path.join(self.tmp.name, 'res.json'))
        return json.load(open(os.path.join(self.tmp.name, 'res.json'), encoding='utf-8'))
    def merge(self, stage, rnd):
        for f in (f'out_{stage}/N{rnd}{stage}_vocab_{rnd}.json', f'reports/N{rnd}_{stage}_done.md'):
            os.makedirs(os.path.dirname(os.path.join(self.repo, f)), exist_ok=True); shutil.copy(os.path.join(self.pr, f), os.path.join(self.repo, f))
    def apply(self):
        self.steward('apply-result', '--result', os.path.join(self.tmp.name, 'res.json'), '--pr-dir', self.pr, '--actions', os.path.join(self.tmp.name, 'act.json'))
        return json.load(open(os.path.join(self.tmp.name, 'act.json'), encoding='utf-8'))
    def human(self, action, **kw):
        a = ['human-action', '--action', action, '--actions', os.path.join(self.tmp.name, 'act.json')]
        for k, v in kw.items(): a += [f'--{k}', str(v)]
        self.steward(*a); return json.load(open(os.path.join(self.tmp.name, 'act.json'), encoding='utf-8'))
    def B(self, A):
        w = [x['word'] for x in A]
        return {'batch': 'N0001', 'checked': len(w), 'reviewed': w, 'gate': {'a_count': len(w), 'checked': len(w), 'reviewed_count': len(w), 'pass': True, 'reason': ''}, 'issues': []}


class FullRound(unittest.TestCase):
    def setUp(self): self.e = Env()
    def tearDown(self): self.e.close()

    def test_two_rounds_to_done(self):
        e = self.e; A1 = jl('Final_0409.json')
        r = e.deliver('A', '0001', A1); self.assertEqual(r['verdict'], 'pass', r)
        e.merge('A', '0001'); act = e.apply(); st = e.state()
        self.assertEqual((st['stage'], st['status'], st['attempt']), ('B', 'waiting', 1)); self.assertIsNone(act['wake']['issue'])
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'reports/check/N0001_A.md')))
        r = e.deliver('B', '0001', e.B(A1)); self.assertEqual(r['verdict'], 'pass', r)
        e.merge('B', '0001'); act = e.apply(); st = e.state()
        self.assertEqual((st['stage'], st['status']), ('C', 'waiting')); self.assertIn('[wake-claude-C] N0001', act['wake']['issue']['title'])
        r = e.deliver('C', '0001', A1); self.assertEqual(r['verdict'], 'pass', r)
        e.merge('C', '0001'); act = e.apply(); st = e.state()
        self.assertEqual((st['round'], st['stage'], st['status']), ('0002', 'A', 'waiting')); self.assertEqual(st['last_ok_round'], '0001')
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'master/N0001C_vocab_0001.json')))
        self.assertGreater(len(open(os.path.join(e.repo, 'used_emoji.txt'), encoding='utf-8').read().splitlines()), 5)
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'metrics/rounds.csv'))); self.assertIn('N0001 整輪正確', e.jobs())
        # 第二輪（最後一輪）
        A2 = jl('Final_0410.json')
        for stage, data in (('A', A2), ('B', e.B(A2)), ('C', A2)):
            r = e.deliver(stage, '0002', data); self.assertEqual(r['verdict'], 'pass', (stage, r['errors'][:3])); e.merge(stage, '0002'); e.apply()
        st = e.state(); self.assertEqual((st['stage'], st['status']), ('done', 'done'))
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'master/batch_05_N0001-N0002.json')))
        self.assertIn('全部完成', e.jobs())

    def test_failures_and_needs_human(self):
        e = self.e; bad = jl('A_0410.json')
        e.set_state(dict(e.state(), round='0002'))
        r = e.deliver('A', '0002', bad); self.assertEqual(r['verdict'], 'content_fail'); self.assertTrue(any('Emoji' in x['msg'] for x in r['errors']))
        act = e.apply(); st = e.state()
        self.assertEqual((st['attempt'], st['status']), (2, 'waiting')); self.assertTrue(act['close_pr']); self.assertIn('[wake-claude-A] N0002 attempt 2', act['wake']['issue']['title'])
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'attempts/N0002-A-try1/check_report.md')))
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'attempts/N0002-A-try1/N0002A_vocab_0002.json')))
        r = e.deliver('A', '0002', bad, attempt=2); self.assertEqual(r['verdict'], 'content_fail')       # 同樣的錯 → 簽章重複
        act = e.apply(); st = e.state()
        self.assertEqual(st['status'], 'needs_human'); self.assertIn('[需人工處理]', act['open_issue']['title']); self.assertIn('錯誤簽章重複', act['open_issue']['title'])

    def test_attempt_limit(self):
        e = self.e; e.set_state(dict(e.state(), attempt=3, last_error_signature='different'))
        r = e.deliver('A', '0001', jl('A_0410.json'), attempt=3); self.assertEqual(r['verdict'], 'content_fail')
        e.apply(); self.assertEqual(e.state()['status'], 'needs_human')

    def test_not_counted_verdicts(self):
        e = self.e; A1 = jl('Final_0409.json')
        self.assertEqual(e.deliver('A', '0001', A1, head_repo='fork/r')['verdict'], 'rejected')
        self.assertEqual(e.deliver('A', '0001', A1, extra_files=['scripts/check_batch.py'])['verdict'], 'rejected')
        self.assertEqual(e.deliver('A', '0001', A1, extra_files=['out_B/N0001B_vocab_0001.json'])['verdict'], 'stale')
        self.assertEqual(e.deliver('A', '0001', A1, agent='codex')['verdict'], 'noncompliant')
        self.assertEqual(e.deliver('A', '0001', A1, attempt=2)['verdict'], 'stale')
        r = e.deliver('A', '0001', A1, report_text='沒有欄位的回報檔\n'); self.assertIn(r['verdict'], ('stale', 'noncompliant', 'content_fail'))
        a = e.state()['attempt']; e.deliver('A', '0001', A1, agent='codex'); e.apply()
        self.assertEqual(e.state()['attempt'], a); self.assertIn('拒絕', e.jobs())

    def test_self_reported_fail_counts(self):
        e = self.e; rep = e.report('A', '0001', 1, 'claude', gate='FAIL｜篇幅用盡，完成 30/50')
        r = e.deliver('A', '0001', jl('Final_0409.json')[:30], report_text=rep); self.assertEqual(r['verdict'], 'content_fail')
        e.apply(); self.assertEqual(e.state()['attempt'], 2)

    def test_c_diff_catches_sneaky_edit(self):
        e = self.e; A1 = jl('Final_0409.json'); e.deliver('A', '0001', A1); e.merge('A', '0001'); e.apply()
        e.deliver('B', '0001', e.B(A1)); e.merge('B', '0001'); e.apply()
        C = json.loads(json.dumps(A1)); C[0]['senses'][0]['zh'] = '偷改的中文義'
        r = e.deliver('C', '0001', C); self.assertEqual(r['verdict'], 'content_fail')
        self.assertTrue(any('diff:unexpected' in x['msg'] for x in r['errors']), r['errors'])

    def test_human_fix_and_actions(self):
        e = self.e; e.set_state(dict(e.state(), status='needs_human', open_issue=12))
        r = e.deliver('A', '0001', jl('Final_0409.json'), agent='claude'); self.assertEqual(r['verdict'], 'stale')   # needs_human 時 AI 交付是過期的
        r = e.deliver('A', '0001', jl('Final_0409.json'), agent='human'); self.assertEqual(r['verdict'], 'pass'); self.assertTrue(r['human_fix'])
        e.merge('A', '0001'); act = e.apply(); st = e.state()
        self.assertEqual((st['stage'], st['status']), ('B', 'waiting')); self.assertEqual(act.get('close_issue'), 12); self.assertIsNone(st['open_issue'])
        self.assertIn('人工修檔', e.jobs())

    def test_human_continue_redo_skip(self):
        e = self.e; e.set_state(dict(e.state(), status='paused'))
        act = e.human('continue'); st = e.state(); self.assertEqual(st['status'], 'waiting'); self.assertIn('[wake-claude-A] N0001', act['wake']['issue']['title'])
        A1 = jl('Final_0409.json'); e.deliver('A', '0001', A1); e.merge('A', '0001'); e.apply()
        e.human('redo', stage='A'); st = e.state()
        self.assertEqual((st['stage'], st['status'], st['attempt']), ('A', 'waiting', 1)); self.assertFalse(os.path.exists(os.path.join(e.repo, 'out_A/N0001A_vocab_0001.json')))
        self.assertTrue([d for d in os.listdir(os.path.join(e.repo, 'attempts')) if 'rollback' in d])
        e.human('skip'); st = e.state(); self.assertEqual((st['round'], st['stage']), ('0002', 'A')); self.assertIn('0001', st['skipped_rounds'])
        e.human('imported', batch='05'); self.assertIn('批 05', open(os.path.join(e.repo, 'master/IMPORTED.md'), encoding='utf-8').read())

    def test_two_human_rounds_pause(self):
        e = self.e; e.set_state(dict(e.state(), consecutive_human_rounds=1))
        act = e.human('skip'); st = e.state(); self.assertEqual(st['status'], 'paused'); self.assertIn('整體暫停', act['open_issue']['title'])

    def test_stall_check(self):
        e = self.e; e.set_state(dict(e.state(), deadline_at='2026-11-01T09:00:00+08:00'))
        e.steward('stall-check', '--actions', os.path.join(e.tmp.name, 'act.json'))
        act = json.load(open(os.path.join(e.tmp.name, 'act.json'), encoding='utf-8')); self.assertIn('[停滯]', act['open_issue']['title']); self.assertIn('停滯', e.jobs())
        self.assertEqual(e.state()['attempt'], 1)                      # 不計 attempt
        e.steward('record-issue', '--number', '9'); e.steward('stall-check', '--actions', os.path.join(e.tmp.name, 'act.json'))
        self.assertIsNone(json.load(open(os.path.join(e.tmp.name, 'act.json'), encoding='utf-8'))['open_issue'])   # 已有 open_issue 不重複開


class Recovery(unittest.TestCase):
    """審查第 1～3 項：復原路徑、symlink、人工修檔失敗不覆寫。"""
    def setUp(self): self.e = Env()
    def tearDown(self): self.e.close()

    def test_stall_then_continue_recovers(self):
        e = self.e; e.set_state(dict(e.state(), deadline_at='2026-11-01T09:00:00+08:00', open_issue=9))
        act = e.human('continue'); st = e.state()
        self.assertEqual(st['status'], 'waiting'); self.assertGreater(st['deadline_at'], NOW); self.assertIsNone(st['open_issue'])
        self.assertEqual(act.get('close_issue'), 9); self.assertIn('[wake-claude-A] N0001', act['wake']['issue']['title'])

    def test_any_pass_clears_open_issue(self):
        e = self.e; e.set_state(dict(e.state(), open_issue=5))
        r = e.deliver('A', '0001', jl('Final_0409.json')); self.assertEqual(r['verdict'], 'pass'); e.merge('A', '0001'); act = e.apply()
        self.assertIsNone(e.state()['open_issue']); self.assertEqual(act.get('close_issue'), 5)

    def test_noncounted_rewake_and_limit(self):
        e = self.e; A1 = jl('Final_0409.json')
        e.deliver('A', '0001', A1, agent='codex'); act = e.apply(); st = e.state()
        self.assertEqual((st['status'], st['attempt'], st['noncount_streak']), ('waiting', 1, 1))
        self.assertIsNotNone(act['wake']['issue']); self.assertTrue(act['close_wake_issues']); self.assertGreater(st['deadline_at'], NOW)
        e.deliver('A', '0001', A1, agent='codex'); e.apply()
        e.deliver('A', '0001', A1, agent='codex'); act = e.apply(); st = e.state()
        self.assertEqual(st['status'], 'needs_human'); self.assertIn('連續 3 次', act['open_issue']['title']); self.assertEqual(st['attempt'], 1)

    def test_streak_reset_by_valid_delivery(self):
        e = self.e; A1 = jl('Final_0409.json')
        e.deliver('A', '0001', A1, agent='codex'); e.apply(); self.assertEqual(e.state()['noncount_streak'], 1)
        e.deliver('A', '0001', A1); e.merge('A', '0001'); e.apply(); self.assertEqual(e.state()['noncount_streak'], 0)

    def test_stale_while_needs_human_does_not_rewake(self):
        e = self.e; e.set_state(dict(e.state(), status='needs_human'))
        e.deliver('A', '0001', jl('Final_0409.json'), agent='claude'); act = e.apply()
        self.assertIsNone(act['wake']); self.assertEqual(e.state()['status'], 'needs_human')

    def test_symlink_rejected(self):
        e = self.e; A1 = jl('Final_0409.json'); e.deliver('A', '0001', A1)
        secret = os.path.join(e.tmp.name, 'secret.txt'); open(secret, 'w').write('TOKEN=abc')
        out = os.path.join(e.pr, 'out_A/N0001A_vocab_0001.json'); os.remove(out); os.symlink(secret, out)
        e.steward('validate-pr', '--pr-json', os.path.join(e.tmp.name, 'pr.json'), '--pr-dir', e.pr, '--out', os.path.join(e.tmp.name, 'res.json'))
        r = json.load(open(os.path.join(e.tmp.name, 'res.json'), encoding='utf-8')); self.assertEqual(r['verdict'], 'rejected'); self.assertIn('symlink', r['reasons'][0])
        e.apply(); self.assertFalse(os.path.exists(os.path.join(e.repo, 'attempts', 'N0001-A-try1')))
        self.assertNotIn('TOKEN', ''.join(open(os.path.join(dp, f), errors='ignore').read() for dp, _, fs in os.walk(e.repo) for f in fs))

    def test_symlink_dir_rejected(self):
        e = self.e; e.deliver('A', '0001', jl('Final_0409.json'))
        real = os.path.join(e.tmp.name, 'elsewhere'); shutil.move(os.path.join(e.pr, 'reports'), real); os.symlink(real, os.path.join(e.pr, 'reports'))
        e.steward('validate-pr', '--pr-json', os.path.join(e.tmp.name, 'pr.json'), '--pr-dir', e.pr, '--out', os.path.join(e.tmp.name, 'res.json'))
        self.assertEqual(json.load(open(os.path.join(e.tmp.name, 'res.json'), encoding='utf-8'))['verdict'], 'rejected')

    def test_human_failures_do_not_overwrite(self):
        e = self.e; e.set_state(dict(e.state(), round='0002', status='needs_human')); bad = jl('A_0410.json')
        e.deliver('A', '0002', bad, agent='human'); e.apply()
        e.deliver('A', '0002', bad, agent='human')
        e.steward('apply-result', '--result', os.path.join(e.tmp.name, 'res.json'), '--pr-dir', e.pr, '--actions', os.path.join(e.tmp.name, 'act.json'))
        names = sorted(os.listdir(os.path.join(e.repo, 'attempts'))); self.assertTrue(names and all('try' not in n for n in names), names)
        self.assertEqual(e.state()['status'], 'needs_human'); self.assertEqual(e.state()['attempt'], 1)


class ReviewFollowups(unittest.TestCase):
    """審查第 4～11 項。"""
    def setUp(self): self.e = Env()
    def tearDown(self): self.e.close()

    def run_round(self, rnd, data):
        e = self.e
        for stage, d in (('A', data), ('B', e.B(data)), ('C', data)):
            r = e.deliver(stage, rnd, d); self.assertEqual(r['verdict'], 'pass', (rnd, stage, r['errors'][:2])); e.merge(stage, rnd); e.apply()

    def test_stage_deadlines_and_c_report(self):
        e = self.e; A1 = jl('Final_0409.json'); e.deliver('A', '0001', A1); e.merge('A', '0001'); e.apply()
        self.assertEqual(e.state()['deadline_at'], '2026-11-01T15:00:00+08:00')           # B 的時限是 5 小時
        e.deliver('B', '0001', e.B(A1)); e.merge('B', '0001'); e.apply(); self.assertEqual(e.state()['deadline_at'], '2026-11-01T13:00:00+08:00')
        e.deliver('C', '0001', A1); e.merge('C', '0001'); e.apply()
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'reports/check/N0001_C.md')))

    def test_continue_not_counted_as_human(self):
        e = self.e; e.set_state(dict(e.state(), status='paused')); e.human('continue')
        self.assertFalse(e.state()['round_stats']['human_in_round'])
        self.run_round('0001', jl('Final_0409.json')); self.assertEqual(e.state()['consecutive_human_rounds'], 0)

    def test_batch_after_skipped_round_is_filled_and_resume(self):
        e = self.e; A1, A2 = jl('Final_0409.json'), jl('Final_0410.json')
        e.human('skip'); self.assertEqual(e.state()['round'], '0002')
        self.run_round('0002', A2); st = e.state(); self.assertEqual(st['status'], 'done')
        self.assertFalse([f for f in os.listdir(os.path.join(e.repo, 'master')) if f.startswith('batch_')])     # 有跳過的輪，不合批
        e.human('redo', stage='A', round='0001'); st = e.state(); self.assertEqual((st['round'], st['stage'], st['status']), ('0001', 'A', 'waiting'))
        self.run_round('0001', A1); st = e.state()
        self.assertEqual((st['round'], st['status']), ('0001', 'done'))                       # 補完回到 done，不重做第 2 輪
        self.assertTrue(os.path.exists(os.path.join(e.repo, 'master/batch_05_N0001-N0002.json')))
        self.assertEqual(st['skipped_rounds'], [])

    def test_redo_other_round_resumes_exact_stage(self):
        e = self.e; A1, A2 = jl('Final_0409.json'), jl('Final_0410.json')
        e.human('skip'); r = e.deliver('A', '0002', A2); e.merge('A', '0002'); e.apply()
        e.set_state(dict(e.state(), attempt=2))                                                # 第 2 輪停在 B 的第 2 次
        e.human('redo', stage='A', round='0001'); self.run_round('0001', A1); st = e.state()
        self.assertEqual((st['round'], st['stage'], st['attempt']), ('0002', 'B', 2))      # skip 與 redo 都算人工，連續 2 輪會 paused，屬正常

    def test_release_emoji(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('steward', STEWARD); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        p = os.path.join(self.e.repo, 'used_emoji.txt'); open(p, 'w', encoding='utf-8').write('💡(lamp)\n🍎(apple)\n')
        m.release_emoji(self.e.repo, [{'word': 'lamp', 'emoji': '💡'}]); self.assertEqual(open(p, encoding='utf-8').read(), '🍎(apple)\n')


class StricterChecks(unittest.TestCase):
    def test_report_lenient(self):
        t = "round: 0001\nSTAGE: A\nAGENT: Claude Code\nATTEMPT: 1\nOUTPUT: out_A/N0001A_vocab_0001.json\nGATE-A: PASS\n---\n"
        self.assertTrue(validate_report.validate(t, 'A', '0001', 1)['ok'])
        self.assertTrue(validate_report.validate(t.replace('round: 0001', 'ROUND: n0001').replace('Claude Code', 'claude'), 'A', '0001', 1)['ok'])
        self.assertEqual(validate_report.validate(t.replace('Claude Code', 'Gemini'), 'A', '0001', 1)['errors'][0]['kind'], 'noncompliant')

    def test_check_batch_new_errors(self):
        with tempfile.TemporaryDirectory() as d:
            data = [json.loads(json.dumps(x)) for x in jl('Final_0409.json')]
            data[0]['pos_list'] = ['n.']; data[1]['senses'][0]['examples'][0]['zh'] = ''; data[2] = {'word': data[2]['word'], 'error': '無法處理'}
            p = os.path.join(d, 'a.json'); json.dump(data, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
            w = os.path.join(d, 'w.txt'); open(w, 'w').write('\n'.join(x['word'] for x in data))
            code, out = run('check_batch.py', p, w, '--band', '50')
        self.assertEqual(code, 1); self.assertIn('多餘欄位', out); self.assertIn('是空的', out); self.assertIn('需重作', out)

    def test_diff_value_mismatch(self):
        A, C, B = jl('A_0409.json'), jl('Cai_0409.json'), jl('B_0409.json')
        with tempfile.TemporaryDirectory() as d:
            out, j = os.path.join(d, 'c.json'), os.path.join(d, 'r.json')
            run('apply_b.py', os.path.join(REAL, 'A_0409.json'), os.path.join(REAL, 'B_0409.json'), '--out', out, '--json', j)
            r = json.load(open(j, encoding='utf-8'))
        extra = [{'word': w, 'path': 'senses[%d].zh' % i} for w, i in (('climate', 0), ('detail', 1), ('truth', 0))]
        block = {'a_count': 50, 'c_count': 50, 'applied': r['applied'], 'skipped': r['skipped'], 'extra_changes': extra, 'nulls': r['nulls']}
        self.assertEqual(diff_check.diff_check(A, C, B, block), [])
        C2 = json.loads(json.dumps(C)); next(x for x in C2 if x['word'] == 'shame')['senses'][0]['examples'][1]['en'] = '被偷換成別的句子 not the fix.'
        self.assertIn('applied_value_mismatch', [e['code'] for e in diff_check.diff_check(A, C2, B, block)])

    def test_validate_b_batch_format(self):
        A = jl('A_0409.json'); B = jl('B_0409.json'); B['gate'] = {'pass': True}
        self.assertTrue(any('batch' in e['msg'] for e in validate_b.validate_b(A, B)[0]))      # 舊版 "04-09" 不合 N####


if __name__ == '__main__':
    unittest.main()
