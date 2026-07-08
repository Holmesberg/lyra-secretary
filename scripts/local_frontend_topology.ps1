$ErrorActionPreference = "Stop"

$script:LyraRepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$script:LyraFrontendDir = Join-Path $script:LyraRepoRoot "frontend"

function Test-WslPublicFrontendSession {
  if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    return $false
  }

  & wsl.exe -e bash -lc "tmux has-session -t lyra-frontend 2>/dev/null" 2>$null
  return $LASTEXITCODE -eq 0
}

function Test-WslPublicFrontendIsolatedDist {
  if (-not (Test-WslPublicFrontendSession)) {
    return $true
  }

  $wslFrontendDir = (& wsl.exe wslpath -a $script:LyraFrontendDir).Trim()
  if (-not $wslFrontendDir) {
    return $false
  }
  $safeWslFrontendDir = $wslFrontendDir.Replace("'", "'\''")

  $probe = "cd '$safeWslFrontendDir' && test -s .next-public/BUILD_ID && grep -q '\[public-topology\] NEXT_DIST_DIR=.next-public' /tmp/frontend.log"

  & wsl.exe -e bash -lc $probe 2>$null
  return $LASTEXITCODE -eq 0
}

function Assert-LocalNextArtifactIsolation {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Reason,

    [ValidateSet("public", "local")]
    [string]$Topology = "local",

    [switch]$AllowPublicFrontendArtifactMutation
  )

  if ($Topology -ne "local") {
    return
  }

  if (-not (Test-WslPublicFrontendSession)) {
    return
  }

  if (Test-WslPublicFrontendIsolatedDist) {
    return
  }

  $envOverride = [Environment]::GetEnvironmentVariable("LYRA_ALLOW_LOCAL_FRONTEND_WHILE_PUBLIC")
  if ([bool]$AllowPublicFrontendArtifactMutation -or $envOverride -eq "1") {
    Write-Warning (
      "Continuing despite active public frontend artifact risk for '$Reason'. " +
      "Restart hosted public frontend with scripts\restart_frontend_wsl.ps1 after this run."
    )
    return
  }

  throw @"
Refusing local frontend artifact mutation while WSL public frontend session 'lyra-frontend' is running.

Reason: $Reason

The public frontend session is active, but it is not proven to be serving the
isolated frontend\.next-public artifact. Local Next build/dev writes
frontend\.next; older public sessions also served from that directory, which
previously caused hosted-public _next chunk 400s and ChunkLoadError in the
browser.

Use one of these explicit paths:
- run the verifier with -Topology public when local frontend proof is not needed;
- stop the public frontend before local artifact mutation, then restart it with scripts\restart_frontend_wsl.ps1;
- pass -AllowPublicFrontendArtifactMutation only for an intentional local proof and restart public immediately after.
"@
}

function Ensure-LocalFrontendDev {
  param(
    [switch]$AllowPublicFrontendArtifactMutation,
    [string]$Reason = "local frontend dev restart"
  )

  Assert-LocalNextArtifactIsolation `
    -Reason $Reason `
    -Topology local `
    -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation

  $outDir = Join-Path $script:LyraRepoRoot "tmp\local-frontend-dev"
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $stdout = Join-Path $outDir "frontend-dev-$stamp.out.log"
  $stderr = Join-Path $outDir "frontend-dev-$stamp.err.log"

  $existing = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($existing) {
    Stop-Process -Id $existing.OwningProcess -Force
    Start-Sleep -Seconds 2
  }

  $env:NEXTAUTH_URL = "http://localhost:3000"
  $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
  $env:NEXT_PUBLIC_BUILD_ID = "local-current"

  $process = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "-p", "3000") `
    -WorkingDirectory $script:LyraFrontendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

  $ready = $false
  $lastError = $null
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try {
      $response = Invoke-WebRequest -UseBasicParsing "http://localhost:3000/api/topology" -TimeoutSec 3
      if ($response.StatusCode -eq 200) {
        $topology = $response.Content | ConvertFrom-Json
        if ($topology.verified_topology -eq $true -and
            $topology.topology_class -eq "local" -and
            $topology.compiled_api_origin -eq "http://localhost:8000") {
          $ready = $true
          break
        }
        $lastError = "unexpected topology response: $($response.Content)"
      }
    } catch {
      $lastError = $_.Exception.Message
    }
  }

  if (-not $ready) {
    Write-Host "Local frontend dev stdout: $stdout"
    Write-Host "Local frontend dev stderr: $stderr"
    Get-Content $stdout -ErrorAction SilentlyContinue | Select-Object -Last 80
    Get-Content $stderr -ErrorAction SilentlyContinue | Select-Object -Last 80
    throw "local frontend dev server did not become topology-ready on localhost:3000. Last error: $lastError"
  }

  Write-Host "Local frontend dev topology-ready on localhost:3000 (pid=$($process.Id))"
  Write-Host "stdout=$stdout"
  Write-Host "stderr=$stderr"
}
