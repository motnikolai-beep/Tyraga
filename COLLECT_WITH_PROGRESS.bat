@echo off
cd \d "%~dp0"
if exist ".venv\Scripts\python.exe" (
 ".venv\Scripts\python.exe" COLLECT_PROJECT.py --include-saves
) else (
 py -3 COLLECT_PROJECT.py --include-saves
)
if errorlevel 1 echo Collection failed - read error above.
pause
