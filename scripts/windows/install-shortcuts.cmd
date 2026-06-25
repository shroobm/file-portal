@echo off
REM Double-click this to create the File Portal Desktop + Start Menu shortcuts.
REM It just runs install-shortcuts.ps1 next to it, no PowerShell prompt needed.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-shortcuts.ps1"
echo.
pause
