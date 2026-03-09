@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%POWERSHELL_EXE%" (
  echo PowerShell not found at "%POWERSHELL_EXE%".
  exit /b 1
)

"%POWERSHELL_EXE%" -ExecutionPolicy Bypass -File "%ROOT_DIR%restart-dev.ps1" %*
exit /b %ERRORLEVEL%
