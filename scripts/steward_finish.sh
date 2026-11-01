#!/usr/bin/env bash
# 總管的收尾：提交並推送狀態檔，再依 actions.json 處理 PR／Issue。由 .github/workflows 呼叫，不給 AI 改（scripts/ 在禁止路徑內）。
# 用法：steward_finish.sh ACTIONS_JSON "提交訊息" [PR編號]
# 需要環境變數：GH_TOKEN、GITHUB_REPOSITORY、NOW（ISO 8601，+08:00）
set -euo pipefail
ACT="$1"; MSG="$2"; PR="${3:-}"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

commit_push() {
  for p in state.json jobs.md master attempts metrics used_emoji.txt reports out_A out_B out_C; do
    if [ -e "$p" ]; then git add -A -- "$p"; fi
  done
  if git diff --cached --quiet; then echo "沒有需要提交的變更"; return 0; fi
  git commit -q -m "steward: $1"
  local ok=0
  for i in 1 2 3; do
    if git pull -q --rebase origin main && git push -q origin HEAD:main; then ok=1; break; fi
    sleep 5
  done
  [ "$ok" = 1 ] || { echo "推送 main 失敗" >&2; exit 1; }
}

jqr() { jq -r "$1" "$ACT"; }

# 1. 先把狀態推上 main（失敗的 PR 檔案已複製進 attempts/，之後才可關 PR）
commit_push "$MSG"

# 2. 關掉舊的喚醒 Issue
if [ "$(jqr '.close_wake_issues // false')" = "true" ]; then
  for n in $(gh issue list --state open --limit 100 --json number,title -q '.[] | select(.title | startswith("[wake-claude]")) | .number'); do
    gh issue close "$n" --comment "總管：階段已處理，關閉喚醒訊號。" || true
  done
fi

# 3. 關閉人工處理 Issue
CI="$(jqr '.close_issue // empty')"
if [ -n "$CI" ]; then gh issue close "$CI" --comment "總管：已有人工動作，關閉。" || true; fi

# 4. 處理 PR（失敗、過期、拒絕）：留言後關閉。合併由 workflow 在呼叫前完成。
if [ -n "$PR" ] && [ "$(jqr '.close_pr // false')" = "true" ]; then
  gh pr comment "$PR" --body "$(jqr '.comment')" || true
  gh pr close "$PR" || true
fi

# 5. 開人工處理／停滯／暫停 Issue（同時最多一個），編號寫回 state.open_issue
if [ "$(jqr '.open_issue != null')" = "true" ]; then
  LABELS=""; for l in $(jqr '.open_issue.labels[]? // empty'); do LABELS="$LABELS --label $l"; done
  # shellcheck disable=SC2086
  URL="$(gh issue create --title "$(jqr '.open_issue.title')" --body "$(jqr '.open_issue.body')" $LABELS)"
  python3 scripts/steward.py record-issue --repo . --now "$NOW" --number "${URL##*/}"
  commit_push "record open issue ${URL##*/}"
fi

# 6. 喚醒下一個 AI（只有 claude 用 Issue；codex 靠自己的排程輪詢）
if [ "$(jqr '.wake.issue != null')" = "true" ]; then
  gh issue create --title "$(jqr '.wake.issue.title')" --body "$(jqr '.wake.issue.body')"
fi
