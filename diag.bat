@echo off
setlocal enabledelayedexpansion
title Coffee POS - Diagnostics

echo =============================================
echo  Coffee POS - Diagnostic Mode
echo =============================================
echo.

echo [STEP 1] Current directory:
cd
echo.
echo [STEP 2] Files in this directory:
dir /b
echo.
pause

echo [STEP 3] docker-compose.yml exists?
if exist "docker-compose.yml" (
    echo  YES - found docker-compose.yml
) else (
    echo  NO  - docker-compose.yml NOT FOUND
    echo        This bat must be in the same folder as docker-compose.yml
    echo        Current path: %CD%
)
echo.
pause

echo [STEP 4] .env exists?
if exist ".env" (
    echo  YES - .env found
) else (
    echo  NO  - .env NOT FOUND, will copy from .env.example
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo  DONE - .env created
    ) else (
        echo  ERROR - .env.example also missing!
    )
)
echo.
pause

echo [STEP 5] Docker version:
docker version
echo.
pause

echo [STEP 6] Node.js check:
node -e "console.log('Node OK: ' + process.version)"
echo.
pause

echo [STEP 7] docker compose config check:
docker compose config --quiet
if errorlevel 1 (
    echo  ERROR in docker-compose.yml
) else (
    echo  docker-compose.yml is valid
)
echo.
pause

echo [STEP 8] Starting docker compose up -d ...
docker compose up -d
echo  Exit code: %errorlevel%
echo.
pause

echo [STEP 9] Checking containers:
docker compose ps
echo.
pause

echo [STEP 10] API health check:
curl -v http://localhost:8000/health
echo.
pause

echo =============================================
echo  Diagnostics complete.
echo =============================================
pause
endlocal
