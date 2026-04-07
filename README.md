# ☕ Coffee POS System

咖啡店進銷存 POS 系統 — 單機 Windows 版本

> ⚠️ **系統文件已拆分，詳細資訊請參閱以下專屬文件：**
> 
> - 📄 **[系統規範與架構 (rule.md)](./rule.md)**
>   包含系統需求、目錄結構架構、開發測試規範以及常見問題（根因對策記錄）。
> - 📄 **[未來發展方向 (future.md)](./future.md)**
>   包含未完成的任務及未來系統升級的規劃與方向。
> - 📄 **[系統發展紀錄 (log.md)](./log.md)**
>   包含系統的歷史版本發布紀錄與已完成功能的開發日誌。

---

## 首次安裝（只需執行一次）

```
1. 解壓縮或 git clone 專案到本機
2. 雙擊執行  setup.bat
3. 依畫面提示完成設定
4. 安裝完成後桌面會出現「Coffee POS 啟動」捷徑
```

或手動建立桌面捷徑：
```powershell
# 在 PowerShell 中，cd 到專案目錄後執行
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

---

## 日常使用

| 動作 | 方法 |
|---|---|
| **啟動系統** | 雙擊桌面「Coffee POS 啟動」或雙擊 `start.bat` |
| **關閉系統** | 雙擊 `stop.bat` |
| **收銀介面** | http://localhost:5173 |
| **API 文件** | http://localhost:8000/docs |

`start.bat` 會自動：
1. 檢查 Docker Desktop 是否執行
2. 啟動 PostgreSQL + FastAPI
3. 等待 API 就緒並執行 Migration
4. 啟動 React 前端
5. 開啟瀏覽器

