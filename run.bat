@echo off
setlocal
cd /d "%~dp0"

:: Enforce Administrator Privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting elevated Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb runas"
    exit /b 0
)

python main.py %*
