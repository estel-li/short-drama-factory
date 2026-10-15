@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "taskPython=%~dp0runtime\python.exe"
if not exist "%taskPython%" set "taskPython=%~dp0.venv\Scripts\python.exe"
if not exist "%taskPython%" (
  echo 缺少应用 Python，请使用完整便携包或先安装 .venv 依赖。
  pause
  exit /b 1
)
"%taskPython%" "%~dp0launcher\start.py" %*
if errorlevel 1 pause
