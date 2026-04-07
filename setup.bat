@echo off
setlocal enabledelayedexpansion

:: Always run from the folder this bat lives in
cd /d "%~dp0"

title Coffee POS - First Time Setup

echo.
echo  ============================================
echo   Coffee POS - First Time Setup Wizard
echo   Working dir: %CD%
echo  ============================================
echo.
echo  This will:
echo    1. Check requirements (Docker, Node.js)
echo    2. Create .env config file
echo    3. Build Docker images
echo    4. Initialize database
echo    5. Import sample data (optional)
echo.
pause

echo.
echo  === Step 1: Checking requirements ===
echo.

docker version >nul 2>&1
if errorlevel 1 (
    echo  [FAIL] Docker is not available or not running.
    echo         Start Docker Desktop, wait for 'Engine Running', then retry.
    pause
    exit /b 1
)
echo  [OK] Docker is available.

node -e "process.exit(0)" >nul 2>&1
if errorlevel 1 (
    echo  [FAIL] Node.js not found.
    echo         Download from https://nodejs.org then retry.
    pause
    exit /b 1
)
echo  [OK] Node.js is available.

if not exist "docker-compose.yml" (
    echo  [FAIL] docker-compose.yml not found.
    echo         Run setup.bat from INSIDE the coffee_pos_pkg folder.
    pause
    exit /b 1
)
echo  [OK] Project files found.

echo.
echo  All requirements OK. Proceeding...
echo.
if not exist "logs"    mkdir logs
if not exist "backups" mkdir backups

echo  === Step 2: Configure .env ===
echo.

if exist ".env" (
    set /p RESET=  .env exists. Reset? (Y/N): 
    if /i "!RESET!"=="Y" goto MAKE_ENV
    goto SKIP_ENV
)

:MAKE_ENV
copy ".env.example" ".env" >nul
set /p DB_PASS=  DB password (Enter = keep 'changeme'): 
if "!DB_PASS!"=="" set DB_PASS=changeme
powershell -Command "(Get-Content .env) -replace 'DB_PASSWORD=changeme','DB_PASSWORD=!DB_PASS!' | Set-Content .env"
echo  [OK] .env created.

:SKIP_ENV
if not exist "frontend\.env.local" (
    echo VITE_API_URL=http://localhost:8000/api/v1>"frontend\.env.local"
    echo  [OK] frontend/.env.local created.
)

echo.
echo  === Step 3: Building Docker images (5-10 min first time) ===
echo.
docker compose build
if errorlevel 1 (
    echo  [FAIL] Build failed.
    pause
    exit /b 1
)
echo  [OK] Images built.

echo.
echo  === Step 4: Initializing database ===
echo.
docker compose up -d
echo  Waiting for database...
:WAIT_DB
timeout /t 3 /nobreak >nul
docker compose exec -T db pg_isready -U pos_user -d coffee_pos >nul 2>&1
if errorlevel 1 goto WAIT_DB
echo  [OK] Database ready.

docker compose exec -T api alembic upgrade head
echo  [OK] Migration done.

echo.
echo  === Step 5: Sample data (optional) ===
set /p SEED=  Import sample menu? (Y/N): 
if /i "!SEED!"=="Y" (
    docker compose exec -T api python scripts/seed_data.py
    echo  [OK] Sample data imported.
)

docker compose down
echo.
echo  ============================================
echo   Setup complete! Run start.bat to launch.
echo  ============================================
echo.
set /p MKLINK=  Create desktop shortcut now? (Y/N): 
if /i "!MKLINK!"=="Y" (
    powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
    echo  [OK] Shortcut created on Desktop.
)
echo.
pause
endlocal
