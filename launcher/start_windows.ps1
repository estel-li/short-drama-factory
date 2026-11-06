# Windows PowerShell 5.1 needs the UTF-8 BOM for Chinese messages.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$LaunchArguments)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskExit = 1
$taskLock = $null
$taskTranscript = $false

function Get-TaskSha256([string]$Path) {
    $taskStream = [IO.File]::OpenRead($Path)
    $taskHasher = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($taskHasher.ComputeHash($taskStream)).Replace('-', '').ToLowerInvariant()
    } finally {
        $taskStream.Dispose()
        $taskHasher.Dispose()
    }
}

try {
    Set-Location -LiteralPath $taskRoot
    [IO.Directory]::CreateDirectory((Join-Path $taskRoot 'logs')) | Out-Null
    try {
        $taskLock = [IO.File]::Open((Join-Path $taskRoot 'logs\startup.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch {
        throw '已有启动窗口正在准备此项目，请等待该窗口完成后再试。'
    }
    Start-Transcript -LiteralPath (Join-Path $taskRoot 'logs\startup.log') -Append | Out-Null
    $taskTranscript = $true
    Write-Host "短剧工厂启动目录：$taskRoot"
    $taskPython = Join-Path $taskRoot 'runtime\python.exe'
    $taskPending = Join-Path $taskRoot 'runtime\python-setup.pending'
    if (!(Test-Path -LiteralPath $taskPython) -and !(Test-Path -LiteralPath $taskPending)) {
        $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
    }
    if (!(Test-Path -LiteralPath $taskPython) -or (Test-Path -LiteralPath $taskPending)) {
        if (![Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64' -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
            throw '自动安装目前支持 Windows x64，请在支持的系统上启动。'
        }
        # Keep this runtime aligned with launcher/build_portable.py.
        $taskVersion = '3.13.16'
        $taskHash = '97dae5274cc54867065e8d5a3226e48c35017ed332a0fdb0e27d5b5821961297'
        $taskDownloads = Join-Path $taskRoot 'data\downloads'
        $taskRuntime = Join-Path $taskRoot 'runtime'
        [IO.Directory]::CreateDirectory($taskDownloads) | Out-Null
        [IO.Directory]::CreateDirectory($taskRuntime) | Out-Null
        $taskArchive = Join-Path $taskDownloads "python-$taskVersion-embed-amd64.zip"
        Write-Host "首次启动：准备项目专用 Python $taskVersion，无需安装到系统。"
        if (!(Test-Path -LiteralPath $taskArchive) -or (Get-TaskSha256 $taskArchive) -ne $taskHash) {
            $taskUrl = "https://www.python.org/ftp/python/$taskVersion/python-$taskVersion-embed-amd64.zip"
            Write-Host '正在从 Python 官方下载运行环境，请保持窗口打开……'
            Invoke-WebRequest -UseBasicParsing -Uri $taskUrl -OutFile "$taskArchive.part" -TimeoutSec 300
            if ((Get-TaskSha256 "$taskArchive.part") -ne $taskHash) {
                throw 'Python 下载校验失败，请重新双击启动以重试。'
            }
            Move-Item -LiteralPath "$taskArchive.part" -Destination $taskArchive -Force
        }
        [IO.File]::WriteAllText($taskPending, $taskVersion)
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $taskZip = [IO.Compression.ZipFile]::OpenRead($taskArchive)
        try {
            foreach ($taskEntry in $taskZip.Entries) {
                $taskDestination = [IO.Path]::GetFullPath((Join-Path $taskRuntime $taskEntry.FullName))
                if (!$taskDestination.StartsWith($taskRuntime + '\', [StringComparison]::OrdinalIgnoreCase)) {
                    throw 'Python 压缩包包含无效路径。'
                }
                if ($taskEntry.Name) {
                    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($taskDestination)) | Out-Null
                    [IO.Compression.ZipFileExtensions]::ExtractToFile($taskEntry, $taskDestination, $true)
                }
            }
        } finally { $taskZip.Dispose() }
        [IO.File]::WriteAllText((Join-Path $taskRuntime 'python313._pth'), "python313.zip`n.`nLib/site-packages`n..`nimport site`n", [Text.UTF8Encoding]::new($false))
        Remove-Item -LiteralPath $taskPending
        $taskPython = Join-Path $taskRuntime 'python.exe'
    }
    # Route native output through the host so the transcript includes install/build errors.
    # Windows PowerShell 5.1 otherwise treats redirected stderr as a terminating error.
    $ErrorActionPreference = 'Continue'
    $LASTEXITCODE = 1
    & $taskPython -X utf8 -u (Join-Path $PSScriptRoot 'prepare.py') @LaunchArguments 2>&1 | ForEach-Object { Write-Host $_ }
    $taskExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
} catch {
    Write-Host "启动未完成：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host '请检查网络和目录写入权限，修复后再次双击；日志：logs\startup.log'
} finally {
    if ($taskTranscript) { Stop-Transcript | Out-Null }
    if ($null -ne $taskLock) { $taskLock.Dispose() }
}
exit $taskExit
