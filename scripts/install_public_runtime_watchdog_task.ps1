param(
    [string]$TaskName = "LyraOS Public Runtime Watchdog",
    [int]$EveryHours = 12,
    [int]$FirstRunMinutesFromNow = 10,
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$watchdogPath = Join-Path $repoRoot "scripts\watch_public_runtime.ps1"
if (-not (Test-Path $watchdogPath)) {
    throw "Watchdog script not found: $watchdogPath"
}

$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogPath`""

$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments -WorkingDirectory $repoRoot
$periodicTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes($FirstRunMinutesFromNow) `
    -RepetitionInterval (New-TimeSpan -Hours $EveryHours) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($logonTrigger, $periodicTrigger) `
    -Settings $settings `
    -Description "Checks LyraOS public runtime at logon and every $EveryHours hours; repairs Cloudflare/local stack when needed." `
    -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName"
Write-Host "Triggers: at logon, then every $EveryHours hours"
Write-Host "First run: about $FirstRunMinutesFromNow minutes from now"
Write-Host "Action: $powershell $arguments"
Write-Host "Logs: $(Join-Path $repoRoot 'tmp\runtime-watchdog')"

if ($RunNow) {
    Write-Host "Starting task now..."
    Start-ScheduledTask -TaskName $TaskName
}
