@echo off
:: Usage: restart-dev.cmd [start|stop|restart|status] [--wsl-shutdown]
:: Thin launcher for restart-dev.ps1 (Windows-native PowerShell implementation).
:: Prefers pwsh (PowerShell 7+) when available; falls back to Windows PowerShell 5.1.
setlocal

set "ROOT_DIR=%~dp0"

where pwsh >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  pwsh -ExecutionPolicy Bypass -File "%ROOT_DIR%restart-dev.ps1" %*
  exit /b %ERRORLEVEL%
)

set "PS5=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS5%" (
  echo ERROR: Neither pwsh nor PowerShell 5 found.
  exit /b 1
)

"%PS5%" -ExecutionPolicy Bypass -File "%ROOT_DIR%restart-dev.ps1" %*
exit /b %ERRORLEVEL%
