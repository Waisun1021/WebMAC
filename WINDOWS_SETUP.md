# WebMAC Windows 完整安裝與執行教學

這份教學適用於 Windows 10／11，並以 PowerShell 執行 WebMAC。測試網站 Spring PetClinic 已經一併放在 `WebMAC/spring-petclinic`，下載這一個 Repository 即可取得兩個專案。

## 1. 建議的資料夾配置

為避免 Maven、Checkstyle、Java 或其他工具遇到中文路徑問題，建議把整個 Repository 放在只有英文字母的短路徑：

```text
D:\projects\
└── WebMAC\
    └── spring-petclinic\
```

不要放在這類路徑：

```text
D:\研究所\開會\agent_project\...
```

WebMAC 本身經過調整後比較能處理中文路徑，但 Spring PetClinic 的 Maven Checkstyle 仍可能把中文顯示成 `????`，進而找不到 `nohttp-checkstyle-suppressions.xml`。

## 2. 安裝必要軟體

需要安裝：

1. Git for Windows
2. Python 3.11（建議使用你目前成功執行的版本）
3. Java JDK 17 或專案要求的更高版本
4. Visual Studio Code（選用）

安裝後開啟新的 PowerShell，逐一確認：

```powershell
git --version
python --version
java -version
```

若 `python` 找不到，可試：

```powershell
py --version
```

## 3. 下載完整專案

建立英文路徑：

```powershell
New-Item -ItemType Directory -Path "D:\projects" -Force
Set-Location "D:\projects"
```

下載你的 WebMAC Fork。這次只需要執行一次 `git clone`，因為測試網站已包含在裡面：

```powershell
git clone https://github.com/Waisun1021/WebMAC.git
```

確認資料夾：

```powershell
Get-ChildItem "D:\projects\WebMAC"
```

應該在 WebMAC 裡看到 `spring-petclinic`、`main.py`、`requirements.txt` 等檔案。

## 4. 啟動 Spring PetClinic

開啟第一個 PowerShell 視窗：

```powershell
Set-Location "D:\projects\WebMAC\spring-petclinic"
.\mvnw.cmd spring-boot:run
```

第一次執行會下載 Maven 套件，可能需要幾分鐘。看到類似下列訊息才代表啟動完成：

```text
Started PetClinicApplication
```

接著用瀏覽器開啟：

```text
http://localhost:8080
```

再確認 WebMAC 使用的頁面：

```text
http://localhost:8080/owners/new
```

執行 WebMAC 期間不要關閉這個 PowerShell 視窗。

### 如果 Maven 出現中文路徑與 Checkstyle 錯誤

典型訊息如下：

```text
Unable to find: D:\????\...\src\checkstyle\nohttp-checkstyle-suppressions.xml
```

解法不是移動 8080，而是把整個 `spring-petclinic` 專案移到英文路徑，例如：

```text
D:\projects\WebMAC\spring-petclinic
```

移動後重新開啟 PowerShell，再執行：

```powershell
Set-Location "D:\projects\WebMAC\spring-petclinic"
.\mvnw.cmd spring-boot:run
```

## 5. 建立 WebMAC Python 虛擬環境

另外開啟第二個 PowerShell 視窗：

```powershell
Set-Location "D:\projects\WebMAC"
py -3.11 -m venv .venv
```

啟用虛擬環境：

```powershell
.\.venv\Scripts\Activate.ps1
```

成功後，命令列前面會出現：

```text
(.venv)
```

若 PowerShell 阻擋啟用腳本，只針對目前視窗放寬限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

更新安裝工具並安裝相依套件：

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m playwright install chromium
```

`flaml.automl is not available` 是 AutoML 選用功能警告。WebMAC 沒有使用 FLAML AutoML 時可先忽略，不是本次測試失敗原因。

## 6. 設定 OpenAI API Key

複製範例檔：

```powershell
Copy-Item dev.env.example dev.env
notepad dev.env
```

把內容改成自己的金鑰：

```dotenv
OPENAI_API_KEY=你的_OpenAI_API_Key
```

儲存後關閉記事本。

重要事項：

- `dev.env` 已被 `.gitignore` 排除，不要強制上傳。
- 不要把 API Key 貼在 README、程式碼、測試紀錄或公開 GitHub。
- 如果曾把真實 Key 上傳到公開 GitHub，應立即到 API 平台撤銷並建立新 Key。
- `The API key specified is not a valid OpenAI format` 代表 Key 是錯的、少貼字元、仍是範例文字，或使用了不適用的 Key。

可檢查環境檔是否存在，但不要把 Key 印出：

```powershell
Test-Path .\dev.env
```

應顯示 `True`。

## 7. 執行前檢查

確認目前路徑：

```powershell
Get-Location
```

應該是：

```text
D:\projects\WebMAC
```

確認虛擬環境中的 Python：

```powershell
python -c "import sys; print(sys.executable)"
```

輸出路徑應包含：

```text
D:\projects\WebMAC\.venv\Scripts\python.exe
```

確認 PetClinic 可連線：

```powershell
Invoke-WebRequest "http://localhost:8080/owners/new" -UseBasicParsing | Select-Object StatusCode
```

應看到：

```text
StatusCode
----------
       200
```

## 8. 執行 WebMAC

確定第一個 PowerShell 正在執行 PetClinic，然後在第二個 PowerShell 執行：

```powershell
Set-Location "D:\projects\WebMAC"
.\.venv\Scripts\Activate.ps1
python main.py
```

執行過程中：

1. WebMAC 會開啟 Chromium。
2. Clarify Agent 讀取 PetClinic 頁面並補齊測試情境。
3. Metamorphosis 階段使用 `model/pict.exe` 產生測試組合。
4. Test Agent 產生並執行 Playwright 測試。
5. 每次執行會在 `run_log/GPT4/日期_時間` 建立紀錄。

目前 `main.py` 有這一行：

```python
test_cases = test_cases[:1]
```

這代表只執行第一筆測試，適合先確認環境。要跑所有產生的測試案例時，可在了解 API 成本與執行時間後移除這一行。

## 9. 查看測試結果

列出最新執行資料夾：

```powershell
Get-ChildItem ".\run_log\GPT4" -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 5 Name, LastWriteTime
```

最新資料夾通常包含：

```text
clarify.txt
metamorphosis.txt
test.txt
test_results.csv
```

用 Excel 開啟最新 CSV：

```powershell
$latest = Get-ChildItem ".\run_log\GPT4" -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Invoke-Item (Join-Path $latest.FullName "test_results.csv")
```

CSV 欄位：

| 欄位 | 意義 |
| --- | --- |
| `test_case` | 實際執行的情境 |
| `test_result` | `PASS`、`FAIL`、`UNKNOWN` 或 `ERROR` |
| `test_summary` | Analyst 對結果的文字說明 |
| `duration_seconds` | 執行秒數 |
| `tokens` | LLM Token 用量 |
| `interactions` | Agent 互動次數 |
| `generated_scripts` | 產生的測試腳本數 |
| `code_errors` | 執行時的程式錯誤數 |

## 10. 常見錯誤排除

### `BrowserType.launch() got an unexpected keyword argument 'devtools'`

目前版本的 `browser.py` 已移除 `devtools` 參數。請確認你執行的是這個 Fork 的最新版：

```powershell
git pull
```

### `UnboundLocalError: browser`

目前版本會先把 `browser` 設為 `None`，只有成功建立後才關閉，已避免這個錯誤。

### `Clarify 階段失敗` 或 `Page loading too long`

依序檢查：

```powershell
Invoke-WebRequest "http://localhost:8080/owners/new" -UseBasicParsing
Test-Path .\dev.env
python -m playwright install chromium
```

並確認 PetClinic 的 PowerShell 視窗仍在執行。

### `ImportError: cannot import name 'trans_to_pict'`

這代表 `model/pict.py` 仍是舊版。更新專案：

```powershell
git pull
```

確認函式存在：

```powershell
Select-String -Path ".\model\pict.py" -Pattern "def trans_to_pict"
```

### API Key 格式警告或 401

重新打開 `dev.env`，確認：

- 變數名稱是 `OPENAI_API_KEY`
- 等號左右沒有多餘引號
- 不是 `replace_with_your_openai_api_key`
- Key 尚未被撤銷

### Port 8080 被占用

查詢使用 8080 的程序：

```powershell
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, State, OwningProcess
```

再查程序名稱：

```powershell
Get-Process -Id <OwningProcess顯示的數字>
```

不要在不知道程序用途時直接強制關閉。

## 11. 將之後的修改上傳到 GitHub

在 WebMAC 專案資料夾執行：

```powershell
Set-Location "D:\projects\WebMAC"
git status
git add .
git status
```

第二次 `git status` 時，務必確認沒有：

```text
dev.env
.env
.venv
```

接著提交並推送：

```powershell
git commit -m "Update Windows setup and test results"
git push origin master
```

如果 GitHub 要求登入，依畫面使用瀏覽器授權或 Personal Access Token；GitHub 不接受帳號密碼直接作為 Git 推送密碼。

## 12. 下次重新執行的最短流程

第一個 PowerShell：

```powershell
Set-Location "D:\projects\WebMAC\spring-petclinic"
.\mvnw.cmd spring-boot:run
```

確認 `http://localhost:8080/owners/new` 可開啟後，第二個 PowerShell：

```powershell
Set-Location "D:\projects\WebMAC"
.\.venv\Scripts\Activate.ps1
python main.py
```

完成後到最新的 `run_log/GPT4/日期_時間/test_results.csv` 查看結果。
