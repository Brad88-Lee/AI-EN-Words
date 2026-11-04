"""scripts/steward_merge.sh 與 scripts/gh_retry.sh 的測試：用假的 gh（PATH 前置）模擬 GitHub 5xx、已合併、head 變更等情境。"""
import json, os, stat, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MERGE = os.path.join(ROOT, 'scripts', 'steward_merge.sh'); RETRY = os.path.join(ROOT, 'scripts', 'gh_retry.sh')
SHA = 'abc123'

FAKE_GH = r'''#!/usr/bin/env bash
# 假 gh：情境檔 $FAKE_DIR/scenario.json：{"view": [[rc, "STATE SHA BRANCH"], ...], "merge": [rc, ...]}，每次呼叫取下一個，用完取最後一個。
# 呼叫紀錄寫到 $FAKE_DIR/calls.log
echo "$*" >> "$FAKE_DIR/calls.log"
python3 - "$@" <<'PY'
import json, os, sys
d = os.environ['FAKE_DIR']; sc = json.load(open(os.path.join(d, 'scenario.json')))
cnt = json.load(open(os.path.join(d, 'count.json'))) if os.path.exists(os.path.join(d, 'count.json')) else {}
kind = 'view' if sys.argv[1:3] == ['pr', 'view'] else 'merge' if sys.argv[1:3] == ['pr', 'merge'] else 'other'
seq = sc.get(kind, [[0, '']]); i = cnt.get(kind, 0); cnt[kind] = i + 1
json.dump(cnt, open(os.path.join(d, 'count.json'), 'w'))
item = seq[min(i, len(seq) - 1)]
if kind == 'merge':
    rc = item
    if rc != 0: print('non-200 OK status code: 503 Service Unavailable', file=sys.stderr)
    # 合併成功後，之後的 view 都回 MERGED（模擬真實狀態）
    if rc == 0: json.dump({'merged': True}, open(os.path.join(d, 'merged.json'), 'w'))
    sys.exit(rc)
rc, out = item
if os.path.exists(os.path.join(d, 'merged.json')) and rc == 0: out = 'MERGED ' + out.split(' ', 1)[1]
print(out); sys.exit(rc)
PY
'''


def run_merge(scenario, pr='1', sha=SHA):
    d = tempfile.mkdtemp(); bindir = os.path.join(d, 'bin'); os.makedirs(bindir)
    gh = os.path.join(bindir, 'gh'); open(gh, 'w').write(FAKE_GH); os.chmod(gh, os.stat(gh).st_mode | stat.S_IEXEC)
    json.dump(scenario, open(os.path.join(d, 'scenario.json'), 'w'))
    env = {**os.environ, 'PATH': bindir + os.pathsep + os.environ['PATH'], 'FAKE_DIR': d, 'MERGE_SLEEP': '0', 'RETRY_SLEEP': '0'}
    r = subprocess.run(['bash', MERGE, pr, sha], capture_output=True, text=True, env=env)
    calls = open(os.path.join(d, 'calls.log')).read().splitlines() if os.path.exists(os.path.join(d, 'calls.log')) else []
    return r.returncode, r.stdout + r.stderr, calls


class Merge(unittest.TestCase):
    def test_merge_first_try(self):
        rc, out, calls = run_merge({'view': [[0, f'OPEN {SHA} claude/N0001-A']], 'merge': [0]})
        self.assertEqual(rc, 0); self.assertIn('合併成功', out); self.assertEqual(sum('pr merge' in c for c in calls), 1)
    def test_retry_on_5xx_then_success(self):
        rc, out, calls = run_merge({'view': [[0, f'OPEN {SHA} b']], 'merge': [1, 1, 0]})
        self.assertEqual(rc, 0); self.assertEqual(sum('pr merge' in c for c in calls), 3)
    def test_merge_reports_error_but_actually_merged(self):
        """gh pr merge 回錯（例如回應階段 502），其實已合併：下一次 view 看到 MERGED 且 head 相同 → 視為成功。"""
        rc, out, calls = run_merge({'view': [[0, f'OPEN {SHA} b'], [0, f'MERGED {SHA} b']], 'merge': [1]})
        self.assertEqual(rc, 0); self.assertIn('已合併', out); self.assertEqual(sum('pr merge' in c for c in calls), 1)
    def test_already_merged_same_head(self):
        rc, out, calls = run_merge({'view': [[0, f'MERGED {SHA} b']], 'merge': [0]})
        self.assertEqual(rc, 0); self.assertEqual(sum('pr merge' in c for c in calls), 0)
    def test_head_changed_is_skip(self):
        rc, out, _ = run_merge({'view': [[0, 'OPEN otherSha b']], 'merge': [0]})
        self.assertEqual(rc, 2)
    def test_closed_is_skip(self):
        rc, out, _ = run_merge({'view': [[0, f'CLOSED {SHA} b']], 'merge': [0]})
        self.assertEqual(rc, 2)
    def test_all_fail(self):
        rc, out, calls = run_merge({'view': [[0, f'OPEN {SHA} b']], 'merge': [1]})
        self.assertEqual(rc, 1); self.assertEqual(sum('pr merge' in c for c in calls), 4)
    def test_view_failing_then_recovering(self):
        rc, out, calls = run_merge({'view': [[1, ''], [1, ''], [0, f'OPEN {SHA} b']], 'merge': [0]})
        self.assertEqual(rc, 0)
    def test_never_uses_delete_branch_flag(self):
        rc, out, calls = run_merge({'view': [[0, f'OPEN {SHA} b']], 'merge': [0]})
        self.assertFalse(any('--delete-branch' in c for c in calls))   # 分支刪除獨立做，失敗不影響結果


class Retry(unittest.TestCase):
    def run_retry(self, n, script):
        d = tempfile.mkdtemp(); f = os.path.join(d, 'cnt')
        r = subprocess.run(['bash', RETRY, str(n), 'bash', '-c', script.replace('CNT', f)], capture_output=True, text=True, env={**os.environ, 'RETRY_SLEEP': '0'})
        return r.returncode, int(open(f).read()) if os.path.exists(f) else 0
    def test_success_after_failures(self):
        rc, n = self.run_retry(4, 'c=$(cat CNT 2>/dev/null || echo 0); c=$((c+1)); echo $c > CNT; [ $c -ge 3 ]')
        self.assertEqual(rc, 0); self.assertEqual(n, 3)
    def test_gives_up_with_last_rc(self):
        rc, n = self.run_retry(3, 'c=$(cat CNT 2>/dev/null || echo 0); echo $((c+1)) > CNT; exit 7')
        self.assertEqual(rc, 7); self.assertEqual(n, 3)
    def test_no_retry_on_success(self):
        rc, n = self.run_retry(3, 'echo 1 > CNT; true')
        self.assertEqual(rc, 0); self.assertEqual(n, 1)


class Workflow(unittest.TestCase):
    def test_steward_yml_uses_merge_script_and_handles_merged_rerun(self):
        s = open(os.path.join(ROOT, '.github', 'workflows', 'steward.yml'), encoding='utf-8').read()
        self.assertIn('bash scripts/steward_merge.sh "$PR" "$SHA"', s)
        self.assertNotIn('gh pr merge', s)                                   # 合併只在腳本裡
        self.assertIn('驗證通過 | PR #$PR：', s)                              # 已合併但沒做完 → 補做；做完 → 略過
        self.assertIn('[ "$MR" = 2 ]', s)
        self.assertIn('Re-run failed jobs', s)                               # 失敗通知告訴人怎麼做
        self.assertIn('gh_retry.sh 3 gh issue create', s)
    def test_jobs_md_line_format_matches_grep(self):
        """workflow 用 grep「驗證通過 | PR #n：」判斷是否已處理，格式必須和 steward.py 寫的一樣。"""
        src = open(os.path.join(ROOT, 'scripts', 'steward.py'), encoding='utf-8').read()
        self.assertIn("'驗證通過', f\"PR #{pr}：", src)
        jobs = open(os.path.join(ROOT, 'jobs.md'), encoding='utf-8').read()
        if '驗證通過 | PR #' in jobs: self.assertIn('驗證通過 | PR #', jobs)


if __name__ == '__main__':
    unittest.main()
