param(
    [switch]$NoBuild,
    [switch]$SkipPublicCheck,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$authoritativeScript = Join-Path $PSScriptRoot "restart_frontend_wsl.ps1"
if (-not (Test-Path -LiteralPath $authoritativeScript)) {
    throw "Authoritative frontend restart script not found: $authoritativeScript"
}

$forwardArgs = @()
if ($NoBuild) {
    $forwardArgs += "-NoBuild"
}
if ($SkipPublicCheck) {
    $forwardArgs += "-SkipPublicCheck"
}

Write-Warning "scripts\restart_public_frontend.ps1 is a compatibility wrapper. The authoritative public frontend restart path is scripts\restart_frontend_wsl.ps1."
Write-Host "Delegating to: $authoritativeScript $($forwardArgs -join ' ')"

if ($DryRun) {
    Write-Host "Dry run only; no frontend process was restarted."
    exit 0
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $authoritativeScript @forwardArgs
if ($LASTEXITCODE -ne 0) {
    throw "Authoritative frontend restart failed with exit code $LASTEXITCODE."
}
