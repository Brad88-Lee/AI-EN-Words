# Phase 0 通訊測試清單（依 HANDOFF §11.4、§12、§13）

狀態標記：✅ 已實測　⬜ 未做　👤 需要使用者操作

## A. 前置：GitHub 設定（👤，HANDOFF §11.5）
- ⬜ Settings → Actions → General → Workflow permissions 選 **Read and write permissions**（否則 ping 無法 push）
- ⬜ 建立標籤 `needs-human`、`skip-diff`
- ⬜ 把本分支的 `.github/workflows/ping.yml`、`pr_probe.yml` 合併進 `main`（`workflow_dispatch`、`repository_dispatch` 只認預設分支上的 workflow）

## B. 環境清單（§11.4）
| 項目 | 結果 |
|---|---|
| 本對話容器（Claude Code 雲端 session）：git clone／push `claude/` 分支 | ✅ 已 push 成功 |
| 本對話容器：Python 3.13.18、git 2.43.0；`pip install emoji` 經 proxy 成功（emoji 2.16.0） | ✅ |
| **Claude routine 的環境**（與本對話容器可能不同） | ⬜ 👤 建好 routine 後，讓它跑一次 `python3 --version; pip install emoji; git push` 並回報 |
| Codex 雲端：clone、開 PR、setup script、網路、Python／emoji | ⬜ 👤 |
| GitHub Actions runner | ⬜ 跑 ping 後確認（`ubuntu-latest` 內建 Python 3、`gh`） |
| 手機 GitHub app：看 Issue 推播、觸發 `workflow_dispatch`、對 PR 加標籤 | ⬜ 👤 |

## C. §12 五項未驗證事項
| # | 項目 | 做法 | 結果 |
|---|---|---|---|
| 1 | Actions 以 API trigger 喚醒 Claude routine | 👤 建 routine 並取得 API trigger；token 才需要放 Actions secret（Public repo，不要貼在對話或檔案） | ⬜ |
| 2 | 喚醒 Codex；Codex 能否排程；排程時如何指定思考檔位 | 👤 在 Codex 雲端試 | ⬜ |
| 3 | routine 能否分別指定模型 | 👤 建 routine 時看有無模型選擇器；回報檔 `MODEL:` 只是自述，不可當證據 | ⬜ |
| 4 | 手機 GitHub app 能否觸發 `workflow_dispatch` | 👤 Actions → ping → Run workflow | ⬜ |
| 5 | 兩個 AI 的 App 開 PR 時的作者身分 | 讓 Claude、Codex 各開一個 PR，看 `pr-probe` 的 job summary（login／type） | ⬜ |

## D. repository_dispatch 串接
1. 👤 Actions → ping → Run workflow（備註填「manual」）→ `test/ping.md` 應多一行 `event=workflow_dispatch`。
2. 觸發鏈：到網頁或用有權限的 token 送 `repository_dispatch` event_type=`ping`。預期 `test/ping.md` 依序多 3 行：`ping` → `ping-chain-1` → `ping-chain-2`。
3. 第 2 行、第 3 行不是人觸發的，若出現就代表「GITHUB_TOKEN 發出的 repository_dispatch 會觸發下一個 run」成立（HANDOFF §12 引用官方文件，這裡是實測）。
4. 若鏈只跑到第 1 行：總管步驟間要改用 PAT 或排程，要回頭改 HANDOFF §12。

## E. 結論欄（做完再填）
- 
