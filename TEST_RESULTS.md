# WebMAC 測試紀錄

本文件整理 2026-09-22 在 Windows 環境，以 Spring PetClinic (`http://localhost:8080`) 執行 WebMAC 的紀錄。原始輸出完整保留在 [`run_log/GPT4`](run_log/GPT4)。

## 執行結果

| 執行時間 | 結果 | 說明 |
| --- | --- | --- |
| `2026_09_22_15_38_07` | 啟動失敗 | Playwright 版本不支援 `chromium.launch(devtools=...)`，且瀏覽器變數尚未建立便進行關閉。 |
| `2026_09_22_15_51_09` | 未完成 | Clarify 與 Metamorphosis 有輸出，但 `test_results.csv` 只有標題列。 |
| `2026_09_22_16_03_21` | 結果格式錯誤 | 測試已執行，但 CSV 寫入的是 Python `Chat` 物件字串，尚未轉換為 PASS/FAIL 與摘要。 |
| `2026_09_22_16_09_47` | **PASS** | CSV 欄位與測試結果已正常輸出。 |

## 最後一次成功測試

- 測試對象：Spring PetClinic 新增 Owner 頁面
- 網址：`http://localhost:8080/owners/new`
- 測試資料：名字 `J Smith`、地址 `LongAddressWithoutSpaces1234567890`、城市 `Los Angeles`、電話 `609-591-6230`
- 預期：`J Smith` 不應成為 Owner
- 實際：頁面顯示 `Telephone must be a 10-digit number`
- 判定：`PASS`
- 執行時間：8.96 秒
- Token：4187
- Agent 互動：4 次
- 產生測試腳本：1 支
- 程式錯誤：0

## 本次為 Windows 執行所做的調整

1. `browser.py` 移除不相容的 `devtools` 參數，並避免瀏覽器啟動失敗時對未建立的 `browser` 呼叫 `close()`。
2. `model/pict.py` 補上 `trans_to_pict()`，從專案根目錄以相對路徑執行 `model/pict.exe`，降低 Windows 中文路徑造成的問題。
3. `main.py` 檢查 Clarify 回傳值與 JSON，避免前一階段失敗後繼續執行。
4. `main.py` 將測試結果寫成清楚的 `PASS`、`FAIL`、`UNKNOWN` 或 `ERROR`，並保存摘要、耗時、Token、互動次數、產生腳本數及程式錯誤數。
5. CSV 使用 `utf-8-sig`，方便 Windows Excel 正確顯示中文。
6. 每完成一筆測試立即 `flush()`，避免程式中途停止後遺失已完成的結果。

## 原始檔案位置

最後一次成功測試位於：

```text
run_log/GPT4/2026_09_22_16_09_47/
├── clarify.txt
├── metamorphosis.txt
├── test.txt
└── test_results.csv
```
