"""Phase 1 PR 2 新增與修改的腳本測試（含真實資料 tests/fixtures/real）。
執行：python3 -m unittest discover -s tests -v   （需要 python3 -m pip install emoji）"""
import json, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
REAL = os.path.join(ROOT, 'tests', 'fixtures', 'real')
sys.path.insert(0, SCRIPTS)
import wordforms, taiwan_terms, validate_report, validate_b, diff_check, error_signature, vocab_schema  # noqa: E402


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout + r.stderr


def jl(name):
    return json.load(open(os.path.join(REAL, name), encoding='utf-8'))


class Articles(unittest.TestCase):
    def test_u_words(self):
        for art, w, ok in [('a', 'unanimous', True), ('an', 'unanimous', False), ('a', 'university', True), ('an', 'umbrella', True),
                           ('a', 'unimportant', False), ('an', 'uninteresting', True), ('a', 'one', True), ('an', 'hour', True), ('a', 'honest', False)]:
            self.assertEqual(wordforms.article_ok(art, w), ok, (art, w))

    def test_letters_and_acronyms(self):
        self.assertTrue(wordforms.article_ok('an', 'x', True)); self.assertFalse(wordforms.article_ok('a', 'x', True))
        self.assertTrue(wordforms.article_ok('a', 'u', True)); self.assertTrue(wordforms.article_ok('an', 'MBA', original='MBA'))
        self.assertTrue(wordforms.article_ok('a', 'UN', original='UN'))        # UN 唸 you-en，用 a
        self.assertFalse(wordforms.article_ok('a', 'FBI', original='FBI'))      # FBI 唸 eff-bee-eye，用 an


class Terms(unittest.TestCase):
    def test_mass_physics_exempt(self):
        self.assertEqual(taiwan_terms.hits(['總質量'], ['科學']), [])
        self.assertEqual([t for t, _ in taiwan_terms.hits(['產品質量'], ['工作與商業'])], ['質量'])
        self.assertIn('項目', [t for t, _ in taiwan_terms.hits(['新創項目'], [])])


class RealCheckScripts(unittest.TestCase):
    def test_extra_real(self):
        code, out = run('check_extra.py', os.path.join(REAL, 'A_0409.json'))
        errs = re.findall(r'^- (\w+)：Emoji', out, flags=re.M)
        self.assertEqual(sorted(errs), ['lift', 'stone'], out)
        self.assertNotIn('a unanimous', out)                      # u- 字誤報已修
        code, out = run('check_extra.py', os.path.join(REAL, 'Final_0409.json'))
        self.assertEqual(code, 0, out); self.assertIn('ERROR 0；WARN 0', out)
        code, out = run('check_extra.py', os.path.join(REAL, 'Final_0410.json'))
        self.assertEqual(code, 0, out)

    def test_batch_real(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'w.txt'); open(p, 'w').write('\n'.join(x['word'] for x in jl('A_0410.json')))
            code, out = run('check_batch.py', os.path.join(REAL, 'A_0410.json'), p, '--band', '50')
            self.assertEqual(code, 1, out)                         # 3 個「抽象概念與其他」並列 ERROR
            self.assertEqual(len(re.findall(r'抽象概念與其他 不可並列', out)), 3)
            self.assertIn('例句中文夾英文', out)                    # speech 的「鼓舞 sent」
            self.assertNotIn('質量', out)                           # mass 的物理義不再警告
            p2 = os.path.join(d, 'w2.txt'); open(p2, 'w').write('\n'.join(x['word'] for x in jl('Final_0410.json')))
            code, out = run('check_batch.py', os.path.join(REAL, 'Final_0410.json'), p2, '--band', '50')
            self.assertEqual(code, 0, out)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as d:
            j = os.path.join(d, 'e.json')
            run('check_extra.py', os.path.join(REAL, 'A_0409.json'), '--json', j)
            e = json.load(open(j, encoding='utf-8'))
            self.assertEqual(sorted(x['word'] for x in e['errors']), ['lift', 'stone'])


class ApplyB(unittest.TestCase):
    def test_reproduces_ai_c_except_known(self):
        with tempfile.TemporaryDirectory() as d:
            out, j = os.path.join(d, 'c.json'), os.path.join(d, 'r.json')
            code, txt = run('apply_b.py', os.path.join(REAL, 'A_0409.json'), os.path.join(REAL, 'B_0409.json'), '--out', out, '--json', j)
            self.assertEqual(code, 0, txt)
            P = json.load(open(out, encoding='utf-8')); C = jl('Cai_0409.json'); A = jl('A_0409.json')
            diffs = []
            for p, c in zip(P, C):
                fp, fc = vocab_schema.flatten(p), vocab_schema.flatten(c)
                diffs += [(p['word'], k) for k in set(fp) | set(fc) if fp.get(k) != fc.get(k)]
            self.assertEqual(sorted(diffs), [('climate', 'senses[0].zh'), ('detail', 'senses[1].zh'), ('truth', 'senses[0].zh')])
            r = json.load(open(j, encoding='utf-8'))
            self.assertEqual((len(r['applied']), len(r['skipped']), len(r['nulls'])), (85, 2, 3))
            self.assertLess(len(r['need_zh_check']), 17)           # 虛詞（冠詞、所有格）改動不再提醒

    def test_diff_check_on_real(self):
        with tempfile.TemporaryDirectory() as d:
            out, j = os.path.join(d, 'c.json'), os.path.join(d, 'r.json')
            run('apply_b.py', os.path.join(REAL, 'A_0409.json'), os.path.join(REAL, 'B_0409.json'), '--out', out, '--json', j)
            r = json.load(open(j, encoding='utf-8'))
            extra = [{'word': w, 'path': 'senses[%d].zh' % i, 'reason': '義項 zh 同步'} for w, i in (('climate', 0), ('detail', 1), ('truth', 0))]
            block = {'a_count': 50, 'c_count': 50, 'applied': r['applied'], 'skipped': r['skipped'], 'extra_changes': extra, 'nulls': r['nulls']}
            A, C, B = jl('A_0409.json'), jl('Cai_0409.json'), jl('B_0409.json')
            self.assertEqual(diff_check.diff_check(A, C, B, block), [])
            b2 = dict(block, extra_changes=extra[:2])                    # 少列一個 extra
            self.assertEqual([e['code'] for e in diff_check.diff_check(A, C, B, b2)], ['unexpected'])
            b3 = dict(block, applied=r['applied'] + [{'word': 'shame', 'path': 'senses[0].zh'}])   # 宣稱套用但沒變
            self.assertIn('claimed_not_applied', [e['code'] for e in diff_check.diff_check(A, C, B, b3)])
            C4 = json.loads(json.dumps(C)); next(x for x in C4 if x['word'] == 'victory')['emoji'] = '✌️'   # B 要求設 null
            self.assertIn('null_missing', [e['code'] for e in diff_check.diff_check(A, C4, B, block)])
            self.assertIn('order', [e['code'] for e in diff_check.diff_check(A, C[::-1], B, block)])


REPORT_C = """ROUND：N0001
stage: C
Agent: Claude
ATTEMPT: 2
OUTPUT: out_C/N0001C_vocab_0001.json
GATE-C: PASS｜筆數 50/50｜套用 12｜跳過 3｜null 2/2
MODEL: unknown
REPORTED_AT: 2026-11-01T12:00:00+08:00
---
{"a_count":50,"c_count":50,"applied":[{"word":"switch","path":"senses[0].zh"}],"skipped":[{"word":"lamp","path":"emoji","reason":"uncertain"}],"extra_changes":[],"nulls":[]}
---
自由文字
"""


class Reports(unittest.TestCase):
    def test_lenient_ok(self):
        r = validate_report.validate(REPORT_C, 'C', '0001', 2)
        self.assertTrue(r['ok'], r['errors'])
        fenced = REPORT_C.replace('{"a_count"', '```json\n{"a_count"').replace('"nulls":[]}', '"nulls":[]}\n```')
        self.assertTrue(validate_report.validate(fenced, 'C', '0001', 2)['ok'])

    def test_kinds(self):
        kinds = lambda t, **k: sorted({e['kind'] for e in validate_report.validate(t, 'C', '0001', 2, **k)['errors']})
        self.assertEqual(kinds(REPORT_C.replace('Agent: Claude', 'Agent: codex')), ['noncompliant'])
        self.assertEqual(kinds(REPORT_C.replace('ATTEMPT: 2', 'ATTEMPT: 1')), ['stale'])
        self.assertEqual(kinds(REPORT_C.replace('N0001', 'N0002', 1)), ['stale'])
        self.assertEqual(kinds(REPORT_C.replace('GATE-C: PASS', 'GATE-C: FAIL')), ['content'])
        no_block = REPORT_C.split('---')[0] + '---\n沒有區塊\n'
        self.assertEqual(kinds(no_block), ['content'])
        self.assertEqual(kinds(REPORT_C.replace('Agent: Claude', 'Agent: human')), ['noncompliant'])
        self.assertEqual(kinds(REPORT_C.replace('Agent: Claude', 'Agent: human'), allow_human=True), [])

    def test_a_report_without_block(self):
        a = "ROUND: N0003\nSTAGE: A\nAGENT: claude\nATTEMPT: 1\nOUTPUT: out_A/N0003A_vocab_0003.json\nGATE-A: PASS｜筆數 50/50｜順序一致｜emoji null 7 個\n---\n備註\n"
        self.assertTrue(validate_report.validate(a, 'A', '0003', 1)['ok'])


class ValidateB(unittest.TestCase):
    def base(self):
        A = jl('A_0409.json'); B = jl('B_0409.json'); B['gate'] = {'pass': True}; return A, B

    def test_real_ok(self):
        A, B = self.base(); self.assertEqual(validate_b.validate_b(A, B)[0], [])

    def test_errors(self):
        A, B = self.base()
        B2 = json.loads(json.dumps(B)); B2['issues'].append({'word': 'shame', 'path': 'senses[5].zh', 'type': 'zh_wrong', 'severity': 'low', 'detail': 'x', 'fix': '羞恥'})
        B2['issues'].append({'word': 'shame', 'path': 'senses[0].zh', 'type': 'zh_wrong', 'severity': 'low', 'detail': 'x', 'fix': None})
        B2['issues'].append({'word': 'shame', 'path': 'topics', 'type': 'topics_bad', 'severity': 'low', 'detail': 'x', 'fix': ['不存在']})
        B2['issues'].append({'word': 'nonexistent', 'path': 'emoji', 'type': 'emoji_bad', 'severity': 'low', 'detail': 'x', 'fix': None})
        B2['checked'] = 49
        msgs = ' | '.join(e['msg'] for e in validate_b.validate_b(A, B2)[0])
        for s in ('不存在', 'null', 'topics', '不在 A', 'checked'): self.assertIn(s, msgs)
        B3 = json.loads(json.dumps(B)); B3['gate'] = {'pass': False, 'reason': 'x'}
        self.assertTrue(any('gate' in e['msg'] for e in validate_b.validate_b(A, B3)[0]))


class Signature(unittest.TestCase):
    def test_order_independent(self):
        e1 = [{'src': 'check_extra', 'word': 'lamp', 'msg': 'emoji13'}, {'src': 'diff_check', 'word': 'x', 'msg': 'diff:unexpected:x.zh'}]
        s1, _ = error_signature.signature([e1]); s2, _ = error_signature.signature([e1[::-1]])
        self.assertEqual(s1, s2)
        s3, _ = error_signature.signature([e1[:1]]); self.assertNotEqual(s1, s3)
        self.assertEqual(error_signature.signature([[]])[0], 'none')


class Misc(unittest.TestCase):
    def test_used_emoji(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'a.json'); out = os.path.join(d, 'u.txt')
            json.dump([{'word': 'lamp', 'emoji': '💡'}, {'word': 'bulb', 'emoji': '💡'}, {'word': 'stone', 'emoji': '🪨'}, {'word': 'x', 'emoji': None}], open(p, 'w', encoding='utf-8'), ensure_ascii=False)
            code, o = run('used_emoji.py', p, '--out', out)
            self.assertEqual(open(out, encoding='utf-8').read(), '💡(lamp)\n'); self.assertIn('略過 Emoji 13+', o)

    def test_constants_in_sync(self):
        for f, name in (('check_batch.py', 'TOPICS'), ('apply_b.py', 'TOP')):
            s = open(os.path.join(SCRIPTS, f), encoding='utf-8').read()
            m = re.search(name + r'="([^"]+)"\.split', s); self.assertTrue(m, f)
            self.assertEqual(m.group(1).split('、'), vocab_schema.TOPICS, f)
        s = open(os.path.join(SCRIPTS, 'check_batch.py'), encoding='utf-8').read()
        m = re.search(r"POS=\{([^}]+)\}", s); self.assertEqual({x.strip("' ") for x in m.group(1).split(',')}, vocab_schema.POS)

    def test_vocab_files(self):
        import glob
        total = 0; prev = None
        for f in sorted(glob.glob(os.path.join(ROOT, 'vocab', 'vocab_*.json'))):
            d = json.load(open(f, encoding='utf-8')); total += d['count']
            self.assertEqual(d['count'], len(d['words']))
            if prev: self.assertEqual(d['seq_from'], prev + 1)
            prev = d['seq_to']
        self.assertEqual(total, 5881)


if __name__ == '__main__':
    unittest.main()
