@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Coffee POS - Starting...

echo.
echo  ============================================
echo   Coffee POS System v1.0  -  Starting...
echo   Dir: %CD%
echo  ============================================
echo.

echo [1/4] Checking Docker...
docker version >nul 2>&1
if errorlevel 1 (
    echo  [FAIL] Docker not running. Start Docker Desktop first.
    pause
    exit /b 1
)
echo  [OK] Docker running.

echo [2/4] Checking Node.js...
node -e "process.exit(0)" >nul 2>&1
if errorlevel 1 (
    echo  [FAIL] Node.js not found. Get from https://nodejs.org
    pause
    exit /b 1
)
echo  [OK] Node.js found.

echo [3/4] Starting Docker services...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo  [OK] .env created.
)
if not exist "logs"    mkdir logs
if not exist "backups" mkdir backups

docker compose up -d --build
if errorlevel 1 (
    echo  [FAIL] Docker failed to start.
    pause
    exit /b 1
)
echo  [OK] Docker services started.

echo  Waiting for API...
set count=0
:WAIT_API
timeout /t 3 /nobreak >nul
curl -sf http://localhost:8000/health >nul 2>&1
if not errorlevel 1 goto API_OK
set /a count+=3
if !count! geq 90 (
    echo  [WARN] API slow. Check: docker compose logs api
    goto START_FRONTEND
)
echo    !count!s...
goto WAIT_API

:API_OK
echo  [OK] API ready: http://localhost:8000
docker compose exec -T api alembic upgrade head >nul 2>&1
echo  [OK] Migration done.

:START_FRONTEND
echo.
echo [4/4] Starting React frontend...
echo  (This window must stay open while POS is running)
echo.
cd frontend

if not exist "node_modules" (
    echo  Installing npm packages - please wait 2-3 minutes...
    echo  You will see progress below:
    echo  ----------------------------------------
    call npm install --legacy-peer-deps
    echo  ----------------------------------------
    if errorlevel 1 (
        echo  [FAIL] npm install failed. See errors above.
        cd ..
        pause
        exit /b 1
    )
    echo  [OK] npm packages installed.
)

if not exist ".env.local" (
    echo VITE_API_URL=http://localhost:8000/api/v1>.env.local
)

echo.
echo  Starting Vite dev server...
echo  When you see "Local: http://localhost:5173", the browser will open.
echo  ----------------------------------------
echo.

:: Open browser after 5 seconds in background
start "" /b cmd /c "timeout /t 8 /nobreak >nul && start http://localhost:5173"

:: Run npm dev in THIS window (keeps visible, shows output)
npm run dev

echo.
echo  [INFO] Frontend stopped.
cd ..
pause
endlocal
