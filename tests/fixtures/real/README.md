# 真實批次資料（用於迴歸測試）

來源：使用者提供，第 4 批第 9、10 份（各 50 字）。內容只有單字資料，Repo 為 Public，HANDOFF §1 已確認無授權疑慮。

| 檔案 | 內容 |
|---|---|
| `A_0409.json`、`A_0410.json` | 當時 A（舊流程）的生成結果 |
| `B_0409.json`、`B_0410.json` | 當時 B 的問題清單（v3 格式，**沒有 `gate` 欄位**） |
| `Cai_0409.json` | 當時 C（AI）的最終檔 |
| `Final_0409.json`、`Final_0410.json` | 人工補正後的匯入版（check 腳本應為 0 ERROR） |

已知事實（測試依據）：
- `A_0409`：2 個 Emoji ERROR（🪨 stone、🛗 lift）；`Cai_0409` 仍保留這兩個（B 標 uncertain，C 不套用）。
- `A_0410`：4 個 Emoji ERROR（🪪 🪚 🛝 🪵）、3 個 topics 並列 ERROR、1 個例句中文夾英文（speech 的「鼓舞 sent」）。
- `apply_b.py` 套 `A_0409`＋`B_0409` 後，與 `Cai_0409` 只差 3 個義項 zh 欄位（climate、detail、truth）。
