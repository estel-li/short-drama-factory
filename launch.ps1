param([switch]$NoBrowser, [int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:FACTORY_PORT = [string]$Port
New-Item -ItemType Directory -Path (Join-Path $taskRoot 'logs') -Force | Out-Null
$taskPython = Join-Path $taskRoot 'runtime\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Application runtime is missing. Use the Windows portable package.' }
$taskBaseUrl = 'http://127.0.0.1:' + $Port
function Get-FactoryHealth {
    # Windows PowerShell 5 decodes charset-less JSON as Latin-1; paths contain Chinese.
    $taskResponse = Invoke-WebRequest -Uri ($taskBaseUrl + '/api/health') -UseBasicParsing -TimeoutSec 5
    $taskJson = [System.Text.Encoding]::UTF8.GetString($taskResponse.RawContentStream.ToArray())
    return ($taskJson | ConvertFrom-Json)
}
$taskHealth = $null
try { $taskHealth = Get-FactoryHealth } catch {}
if ($null -ne $taskHealth -and $taskHealth.version -notlike '2.*') { throw 'An older panel is using this port. Close the old panel process and launch again.' }
if ($null -ne $taskHealth -and $taskHealth.application_root -and $taskHealth.application_root -ne $taskRoot) { throw 'Another application directory is using this port. Start with launch.ps1 -Port <free-port>.' }
if ($null -eq $taskHealth) {
    $taskScript = Join-Path $taskRoot 'launcher\serve.py'
    Start-Process -FilePath $taskPython -ArgumentList @('-u', ('"' + $taskScript + '"')) -WorkingDirectory $taskRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $taskRoot 'logs/panel.stdout.log') `
        -RedirectStandardError (Join-Path $taskRoot 'logs/panel.stderr.log') | Out-Null
    for ($taskAttempt = 0; $taskAttempt -lt 30; $taskAttempt++) {
        try { $taskHealth = Get-FactoryHealth; break } catch {}
        Start-Sleep -Seconds 1
    }
    if ($null -eq $taskHealth) { throw 'Panel startup failed. See logs/panel.stderr.log.' }
}
if (-not $NoBrowser) { Start-Process $taskBaseUrl }
Write-Host ('Short Drama Factory is ready: ' + $taskBaseUrl)
