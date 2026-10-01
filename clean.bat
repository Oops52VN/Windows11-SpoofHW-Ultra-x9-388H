@echo off
setlocal
cd /d "%~dp0"

echo ====================================================================
echo   SPOOFHW - WORKSPACE HOUSEKEEPING ^& CLEANUP SCRIPT
echo ====================================================================
echo.
echo Cleaning PyInstaller build cache, Python bytecode, and temp files...

:: Remove Python bytecode cache
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

:: Remove PyInstaller temporary directories and spec
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "run.spec" del /f /q "run.spec"

:: Remove legacy/temporary search files if any
if exist "regsearch.txt" del /f /q "regsearch.txt"
if exist "search.ps1" del /f /q "search.ps1"
if exist "search2.ps1" del /f /q "search2.ps1"

:: Remove build artifacts
if exist "*.pdb" del /f /q "*.pdb"
if exist "*.obj" del /f /q "*.obj"
if exist "%TEMP%\SpoofHW_*.xml" del /f /q "%TEMP%\SpoofHW_*.xml"

echo.
echo ====================================================================
echo [OK] Workspace cleanup completed successfully.
echo ====================================================================
