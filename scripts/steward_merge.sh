#!/usr/bin/env bash
# 總管的合併步驟：把驗證通過的 PR squash 合併到 main，GitHub 5xx 時重試，並正確處理「其實已經合併」的情況。
# 用法：steward_merge.sh PR編號 HEAD_SHA
# 結束碼：0＝已合併（含本來就已合併且 head 相同）；2＝PR 已更新或關閉（略過，交給新事件）；1＝重試後仍失敗。
# 分支刪除另外做，失敗不影響結果。需要 GH_TOKEN。MERGE_SLEEP 可覆寫重試間隔（測試用）。
set -u
PR="$1"; SHA="$2"
SLEEPS=(5 15 30)

pr_info() {   # 印出 "STATE HEAD_SHA BRANCH"；gh 失敗時印空字串
  gh pr view "$PR" --json state,headRefOid,headRefName -q '.state + " " + .headRefOid + " " + .headRefName' 2>/dev/null || true
}

check_done() { # 已合併且 head 相同 → 0；head 變了或已關閉 → 2；仍 open 且 head 相同 → 1；查不到 → 3
  local info; info="$(pr_info)"
  [ -n "$info" ] || return 3
  local state head; state="${info%% *}"; head="$(echo "$info" | awk '{print $2}')"
  if [ "$head" != "$SHA" ]; then echo "PR #$PR 的 head 已變（$head），略過"; return 2; fi
  case "$state" in
    MERGED) echo "PR #$PR 已合併（head 相同）"; return 0 ;;
    OPEN) return 1 ;;
    *) echo "PR #$PR 已 $state，略過"; return 2 ;;
  esac
}

for ((i = 0; i <= ${#SLEEPS[@]}; i++)); do
  check_done; r=$?
  if [ "$r" = 0 ] || [ "$r" = 2 ]; then exit "$r"; fi
  if [ "$r" = 1 ] && gh pr merge "$PR" --squash --match-head-commit "$SHA"; then
    echo "PR #$PR 合併成功"; exit 0
  fi
  if ((i < ${#SLEEPS[@]})); then
    s="${MERGE_SLEEP:-${SLEEPS[$i]}}"; echo "合併未成功（第 $((i + 1)) 次），$s 秒後重試" >&2; sleep "$s"
  fi
done
check_done; r=$?
if [ "$r" = 0 ] || [ "$r" = 2 ]; then exit "$r"; fi
echo "PR #$PR 重試後仍無法合併" >&2; exit 1
