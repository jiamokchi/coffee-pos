@echo off
cd /d "%~dp0"
title Coffee POS - API Diagnostic Test

echo.
echo === Coffee POS API Test ===
echo.

echo [1] Version check (should say 1.1.0):
curl -s http://localhost:8000/health
echo.
echo.

echo [2] Create ingredient:
curl -s -X POST "http://localhost:8000/api/v1/ingredients" ^
  -H "Content-Type: application/json" ^
  -d "{"name":"test_milk","unit":"ml","min_stock_level":0}"
echo.
echo.

echo [3] Create product:
curl -s -X POST "http://localhost:8000/api/v1/products" ^
  -H "Content-Type: application/json" ^
  -d "{"name":"test_latte","price":120,"tax_type":"TAX","bom":[]}"
echo.
echo.

echo [4] Last 40 lines of API log:
docker compose logs --tail=40 api
echo.

pause
