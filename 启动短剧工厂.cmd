@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0"
if errorlevel 1 exit /b 1
chcp 65001 >nul
if exist "launcher\start_windows.ps1" goto launch
echo Missing launcher files in "%CD%". Please extract the complete package.
set "taskExit=1"
goto finish
:launch
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "launcher\start_windows.ps1" %*
set "taskExit=%errorlevel%"
:finish
if not "%taskExit%"=="0" pause
popd
exit /b %taskExit%
