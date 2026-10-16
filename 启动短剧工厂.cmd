@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0"
if errorlevel 1 exit /b 1
chcp 65001 >nul
set "taskPython=runtime\python.exe"
if exist "%taskPython%" goto launch
set "taskPython=.venv\Scripts\python.exe"
if exist "%taskPython%" goto launch
echo 未找到应用 Python。已检查当前应用目录中的 runtime 和 .venv。
echo 应用目录："%CD%"
echo 请完整解压便携包，或按 README.md 的源码安装步骤建立环境。
set "taskExit=1"
goto finish
:launch
"%taskPython%" -X utf8 "launcher\start.py" %*
set "taskExit=%errorlevel%"
:finish
if not "%taskExit%"=="0" pause
popd
exit /b %taskExit%
