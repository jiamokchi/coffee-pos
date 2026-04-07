@echo off
setlocal
cd /d "%~dp0"
title Coffee POS - Stopping...
echo.
echo  Stopping Coffee POS...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173 "') do (
    taskkill /f /pid %%a >nul 2>&1
)
taskkill /f /fi "WINDOWTITLE eq CoffeePOS-Frontend" >nul 2>&1
echo  [OK] Frontend stopped.
docker compose down
echo  [OK] Docker stopped.
echo.
echo  Done. Goodbye!
pause
endlocal
