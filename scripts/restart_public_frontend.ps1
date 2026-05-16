$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $RepoRoot "frontend"
$StdoutLog = Join-Path $env:TEMP "lyra-next-start-public.out.log"
$StderrLog = Join-Path $env:TEMP "lyra-next-start-public.err.log"

Push-Location $FrontendRoot
try {
    Write-Host "Building frontend for public topology..."
    npm run build:public

    $existing = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($existing) {
        Write-Host "Stopping existing frontend process on port 3000: $($existing.OwningProcess)"
        Stop-Process -Id $existing.OwningProcess -Force
        Start-Sleep -Seconds 2
    }

    Remove-Item -LiteralPath $StdoutLog, $StderrLog -ErrorAction SilentlyContinue
    Write-Host "Starting public frontend on port 3000..."
    $process = Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList @("run", "start:public") `
        -WorkingDirectory $FrontendRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -PassThru

    $listening = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        $listener = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($listener) {
            Write-Host "Frontend is listening on port 3000. start_pid=$($process.Id) listen_pid=$($listener.OwningProcess)"
            $listening = $true
            break
        }
    }

    if (-not $listening) {
        Write-Error "Frontend did not start listening on port 3000."
    }
}
finally {
    Pop-Location
}

Write-Host "Verifying public runtime topology..."
Push-Location $RepoRoot
try {
    node scripts/verify_runtime_topology.mjs --topology public
}
finally {
    Pop-Location
}
