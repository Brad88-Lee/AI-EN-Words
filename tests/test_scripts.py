"""以 tests/fixtures 驗證 scripts/check_batch.py 與 scripts/check_extra.py。
執行：python3 -m unittest discover -s tests -v   （需要 pip install emoji）"""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, 'tests', 'fixtures')
SCRIPTS = os.path.join(ROOT, 'scripts')


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout


def fx(name):
    return os.path.join(FIX, name)


def warns(out):
    """取出「警告／WARN」段落的各行。"""
    for key in ('## 警告明細', '## WARN'):
        if key in out:
            return [l for l in out.split(key, 1)[1].splitlines() if l.startswith('- ')]
    return []


class OkSet(unittest.TestCase):
    def test_check_batch_no_warn(self):
        code, out = run('check_batch.py', fx('hyphen_apostrophe_ok.json'), fx('hyphen_apostrophe_ok_words.txt'))
        self.assertEqual(code, 0, out)
        self.assertEqual(warns(out), [], out)

    def test_check_extra_no_warn(self):
        code, out = run('check_extra.py', fx('hyphen_apostrophe_ok.json'))
        self.assertEqual(code, 0, out)
        self.assertEqual(warns(out), [], out)


class BadSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.batch = run('check_batch.py', fx('hyphen_apostrophe_bad.json'), fx('hyphen_apostrophe_bad_words.txt'))
        _, cls.extra = run('check_extra.py', fx('hyphen_apostrophe_bad.json'))

    def has(self, out, word, text):
        self.assertTrue(any(word in l and text in l for l in warns(out)), f'{word} / {text}\n{out}')

    def test_email_spelling(self):    self.has(self.batch, 'e-mail', 's0e0 英文例句可能不含')
    def test_sit_down_for_sit_in(self): self.has(self.batch, 'sit-in', 's0e1 英文例句可能不含')
    def test_trade_off_for_trade_in(self): self.has(self.batch, 'trade-in', 's0e1 英文例句可能不含')
    def test_well_behaved(self):      self.has(self.batch, 'well-being', 's0e2 英文例句可能不含')
    def test_compound_only(self):     self.has(self.extra, 'part-time', '複合詞內')
    def test_a_xray(self):            self.has(self.extra, 'x-ray', '冠詞可能不對：a x')
    def test_a_up_to_date(self):      self.has(self.extra, 'up-to-date', '冠詞可能不對：a up')


class Units(unittest.TestCase):
    def test_vocab_json_word_list(self):
        vocab = {"round": "0001", "count": 2, "words": [{"seq": 1, "word": "check-in"}, {"seq": 2, "word": "o'clock"}]}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'vocab_0001.json')
            json.dump(vocab, open(p, 'w', encoding='utf-8'))
            data = [e for e in json.load(open(fx('hyphen_apostrophe_ok.json'), encoding='utf-8')) if e['word'] in ('check-in', "o'clock")]
            q = os.path.join(d, 'a.json')
            json.dump(data, open(q, 'w', encoding='utf-8'), ensure_ascii=False)
            code, out = run('check_batch.py', q, p)
            self.assertEqual(code, 0, out)

    def test_exit_code_on_error(self):
        with tempfile.TemporaryDirectory() as d:
            lst = os.path.join(d, 'w.txt'); open(lst, 'w').write('1. check-in\n2. missingword\n')
            data = [e for e in json.load(open(fx('hyphen_apostrophe_ok.json'), encoding='utf-8')) if e['word'] == 'check-in']
            q = os.path.join(d, 'a.json'); json.dump(data, open(q, 'w', encoding='utf-8'), ensure_ascii=False)
            code, out = run('check_batch.py', q, lst)
            self.assertEqual(code, 1, out)

    def test_history_directory(self):
        with tempfile.TemporaryDirectory() as d:
            h = os.path.join(d, 'hist'); os.mkdir(h)
            json.dump([{"word": "lamp", "emoji": "💡"}], open(os.path.join(h, 'h.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            entry = json.load(open(fx('hyphen_apostrophe_ok.json'), encoding='utf-8'))[0]
            entry['emoji'] = '💡'
            q = os.path.join(d, 'a.json'); json.dump([entry], open(q, 'w', encoding='utf-8'), ensure_ascii=False)
            code, out = run('check_extra.py', q, '--history', h)
            self.assertIn('lamp', out)


if __name__ == '__main__':
    unittest.main()
