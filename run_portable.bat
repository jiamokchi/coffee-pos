@echo off
setlocal
echo ==========================================
echo   Coffee POS Portable Starter (No Docker)
echo ==========================================

:: 檢查 Python 是否安裝
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.9+ 
    pause
    exit /b
)

:: 設定環境變數
set USE_SQLITE=True
set APP_ENV=production

:: 如果資料夾不存在，嘗試安裝依賴 (僅第一次)
if not exist "venv" (
    echo [資訊] 第一次啟動，正在建立虛擬環境...
    python -m venv venv
    call venv\Scripts\activate
    echo [資訊] 正在安裝必要套件...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: 建立存放資料的資料夾
if not exist "data" mkdir data

:: 執行資料庫遷移
echo [資訊] 檢查並更新資料庫結構...
alembic upgrade head

:: 啟動伺服器
echo [成功] 系統正在啟動...
echo 請在瀏覽器開啟: http://localhost:8000
echo.
echo 按下 Ctrl+C 可停止系統
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
