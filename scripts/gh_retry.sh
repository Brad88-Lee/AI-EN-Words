#!/usr/bin/env bash
# 對 gh／git 等會碰 GitHub API 的指令加重試（GitHub 偶發 502／503，2026-11-03、11-04 各讓總管失敗一次）。
# 用法：gh_retry.sh 次數 指令 [參數...]；回傳最後一次的結束碼。間隔 5、15、30、60 秒（RETRY_SLEEP 可覆寫，測試用）。
set -u
N="$1"; shift
SLEEPS=(5 15 30 60 60 60)
rc=0
for ((i = 1; i <= N; i++)); do
  "$@" && exit 0
  rc=$?
  if ((i < N)); then
    s="${RETRY_SLEEP:-${SLEEPS[$((i - 1 < ${#SLEEPS[@]} ? i - 1 : ${#SLEEPS[@]} - 1))]}}"
    echo "gh_retry：第 $i 次失敗（rc=$rc），$s 秒後重試：$*" >&2
    sleep "$s"
  fi
done
exit "$rc"
