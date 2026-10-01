@echo off
setlocal
title SpoofHW - Python Standalone Binary Builder
cd /d "%~dp0"

echo ====================================================================
echo   SPOOFHW - STANDALONE EXECUTABLE BUILD PIPELINE (PYINSTALLER)      
echo ====================================================================
echo.

:: 1. Verify PyInstaller presence
where pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] PyInstaller not detected. Attempting installation via pip...
    pip install pyinstaller
    if %errorLevel% neq 0 (
        echo [X] ERROR: Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo [*] PyInstaller detected.
echo [*] Building standalone run.exe with Administrator execution level...

:: 2. Build single-file executable with embedded UAC admin execution level
pyinstaller --noconfirm --clean --onefile ^
    --name run ^
    --uac-admin ^
    --hidden-import winreg ^
    --hidden-import ctypes ^
    main.py

if %errorLevel% neq 0 (
    echo.
    echo [X] Build failed! Check PyInstaller output above.
    pause
    exit /b 1
)

:: 3. Copy executable to root directory for drop-in compatibility
if exist "dist\run.exe" (
    copy /y "dist\run.exe" "run.exe" >nul
    echo.
    echo [OK] Successfully built standalone executable -> run.exe
)

echo.
echo ====================================================================
echo [OK] BUILD PIPELINE COMPLETED SUCCESSFULLY!
echo ====================================================================
echo.
pause
