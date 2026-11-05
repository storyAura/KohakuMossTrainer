@echo off
rem Quick start: opens the Chinese menu in scripts\install\quickstart.ps1 (this file stays ASCII for cmd).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install\quickstart.ps1"
if errorlevel 1 pause
