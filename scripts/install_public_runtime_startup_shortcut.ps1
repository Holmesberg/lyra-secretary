param(
    [string]$ShortcutName = "LyraOS Public Runtime Watchdog"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$watchdogPath = Join-Path $repoRoot "scripts\watch_public_runtime.ps1"
if (-not (Test-Path $watchdogPath)) {
    throw "Watchdog script not found: $watchdogPath"
}

$startupDir = [Environment]::GetFolderPath("Startup")
if (-not $startupDir) {
    throw "Windows Startup folder was not found for this user."
}

$shortcutPath = Join-Path $startupDir "$ShortcutName.lnk"
$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogPath`""

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershell
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $repoRoot
$shortcut.WindowStyle = 7
$shortcut.Description = "Starts and repairs LyraOS public runtime at Windows logon."
$shortcut.Save()

Write-Host "Installed startup shortcut: $shortcutPath"
Write-Host "Action: $powershell $arguments"
