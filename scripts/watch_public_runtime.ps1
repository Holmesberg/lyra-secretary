param(
    [switch]$NoRepair,
    [switch]$ReadOnly,
    [switch]$SkipRelay,
    [switch]$AllowFullBuild,
    [int]$TimeoutSeconds = 20,
    [string]$LogDir = ""
)

$ErrorActionPreference = "Stop"

if ($ReadOnly) {
    $NoRepair = $true
    $SkipRelay = $true
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "== $Message =="
}

function Test-HttpEndpoint([string]$Name, [string]$Uri, [int]$Timeout) {
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec $Timeout
        return [pscustomobject]@{
            Name = $Name
            Uri = $Uri
            Ok = $true
            StatusCode = [int]$response.StatusCode
            Error = $null
        }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
            } catch {
                $statusCode = $null
            }
        }
        return [pscustomobject]@{
            Name = $Name
            Uri = $Uri
            Ok = $false
            StatusCode = $statusCode
            Error = $_.Exception.Message
        }
    }
}

function Write-CheckResult($Result) {
    $status = if ($Result.Ok) { "PASS" } else { "FAIL" }
    $code = if ($null -ne $Result.StatusCode) { $Result.StatusCode } else { "n/a" }
    Write-Host "$status $($Result.Name) $code $($Result.Uri)"
    if (-not $Result.Ok -and $Result.Error) {
        Write-Host "  $($Result.Error)"
    }
}

function Start-OpenClawOperatorRelay([string]$RepoRoot) {
    Write-Step "Ensuring OpenClaw operator relay"
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\start_openclaw_operator_relay.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "OpenClaw operator relay start failed."
    }
}

function Ensure-OpenClawOperatorRelay([string]$RepoRoot, [bool]$Skip) {
    if ($Skip) {
        Write-Step "Skipping OpenClaw operator relay"
        Write-Host "Relay start skipped by -ReadOnly/-SkipRelay; no runtime process state changed."
        return
    }

    Start-OpenClawOperatorRelay $RepoRoot
}

function Test-StaticAssetGraph([string]$Name, [string]$BaseUri, [int]$Timeout) {
    $failures = @()
    try {
        $response = Invoke-WebRequest -Uri $BaseUri -UseBasicParsing -TimeoutSec $Timeout
        $matches = [regex]::Matches(
            $response.Content,
            "/_next/static/(?:chunks|css)/[^`"'\s<>\\]+"
        )
        $assets = @($matches | ForEach-Object { $_.Value } | Sort-Object -Unique)
        foreach ($asset in $assets) {
            $assetUri = [Uri]::new([Uri]$BaseUri, $asset).AbsoluteUri
            try {
                $assetResponse = Invoke-WebRequest -Uri $assetUri -Method Head -UseBasicParsing -TimeoutSec $Timeout
                if ([int]$assetResponse.StatusCode -ne 200) {
                    $failures += "$($assetResponse.StatusCode) $asset"
                }
            } catch {
                $failures += "ERR $asset $($_.Exception.Message)"
            }
        }
        return [pscustomobject]@{
            Name = $Name
            Uri = $BaseUri
            Ok = ($failures.Count -eq 0 -and $assets.Count -gt 0)
            StatusCode = [int]$response.StatusCode
            Error = if ($failures.Count -gt 0) { ($failures -join "; ") } elseif ($assets.Count -eq 0) { "no Next static assets found" } else { $null }
            AssetCount = $assets.Count
        }
    } catch {
        return [pscustomobject]@{
            Name = $Name
            Uri = $BaseUri
            Ok = $false
            StatusCode = $null
            Error = $_.Exception.Message
            AssetCount = 0
        }
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $LogDir) {
    $LogDir = Join-Path $repoRoot "tmp\runtime-watchdog"
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$transcriptPath = Join-Path $LogDir "watchdog-$timestamp.log"
Start-Transcript -Path $transcriptPath -Append | Out-Null

try {
    Set-Location $repoRoot
    Write-Host "LyraOS public runtime watchdog"
    Write-Host "Started: $(Get-Date -Format o)"
    Write-Host "Repo: $repoRoot"
    Write-Host "Log: $transcriptPath"

    Write-Step "Checking local runtime"
    $localFrontend = Test-HttpEndpoint "local_frontend" "http://localhost:3000/" $TimeoutSeconds
    $localApi = Test-HttpEndpoint "local_api" "http://localhost:8000/v1/health" $TimeoutSeconds
    Write-CheckResult $localFrontend
    Write-CheckResult $localApi

    Write-Step "Checking public runtime"
    $publicFrontend = Test-HttpEndpoint "public_frontend" "https://lyraos.org/" $TimeoutSeconds
    $publicApi = Test-HttpEndpoint "public_api" "https://api.lyraos.org/v1/health" $TimeoutSeconds
    Write-CheckResult $publicFrontend
    Write-CheckResult $publicApi

    $localOk = $localFrontend.Ok -and $localApi.Ok
    $publicOk = $publicFrontend.Ok -and $publicApi.Ok
    $needsFrontendRepair = $false

    if ($publicOk) {
        Write-Step "Verifying public topology"
        node (Join-Path $repoRoot "scripts\verify_runtime_topology.mjs") --topology public --skip-browser
        if ($LASTEXITCODE -ne 0) {
            throw "public topology verification failed."
        }

        Write-Step "Verifying public static asset graph"
        $publicAssets = Test-StaticAssetGraph "public_static_assets" "https://lyraos.org/" $TimeoutSeconds
        Write-CheckResult $publicAssets
        if ($publicAssets.Ok) {
            Write-Host "Static assets referenced by public HTML: $($publicAssets.AssetCount)"
            Ensure-OpenClawOperatorRelay $repoRoot ([bool]$SkipRelay)
            Write-Host "Runtime is clean."
            exit 0
        }

        $needsFrontendRepair = $true
        Write-Host "Static asset graph failed: $($publicAssets.Error)"
        if ($NoRepair) {
            throw "public runtime has broken static assets and repair is disabled."
        }
    }

    if ($NoRepair) {
        throw "public runtime is unhealthy and repair is disabled."
    }

    if ($needsFrontendRepair) {
        Write-Step "Repairing public frontend static asset graph"
        powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\restart_frontend_wsl.ps1")
        if ($LASTEXITCODE -ne 0) {
            throw "public frontend restart failed."
        }
    } elseif ($localOk) {
        Write-Step "Repairing Cloudflare tunnel only"
        powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\restart_cloudflared_wsl.ps1") -ForceRestart
        if ($LASTEXITCODE -ne 0) {
            throw "Cloudflare tunnel restart failed."
        }
    } else {
        Write-Step "Repairing local stack and Cloudflare tunnel"
        $recoveryArgs = @(
            "-ExecutionPolicy", "Bypass",
            "-File", (Join-Path $repoRoot "scripts\start_public_after_reboot.ps1"),
            "-DockerWaitSeconds", "240"
        )
        if (-not $AllowFullBuild) {
            $recoveryArgs += "-NoBuild"
        }
        powershell @recoveryArgs
        if ($LASTEXITCODE -ne 0) {
            throw "public stack recovery failed."
        }
    }

    Write-Step "Rechecking public runtime after repair"
    Start-Sleep -Seconds 5
    node (Join-Path $repoRoot "scripts\verify_runtime_topology.mjs") --topology public --skip-browser
    if ($LASTEXITCODE -ne 0) {
        throw "public topology verification failed after repair."
    }
    $publicFrontendAfter = Test-HttpEndpoint "public_frontend_after" "https://lyraos.org/" $TimeoutSeconds
    $publicApiAfter = Test-HttpEndpoint "public_api_after" "https://api.lyraos.org/v1/health" $TimeoutSeconds
    Write-CheckResult $publicFrontendAfter
    Write-CheckResult $publicApiAfter

    if (-not ($publicFrontendAfter.Ok -and $publicApiAfter.Ok)) {
        throw "public runtime remains unhealthy after repair."
    }

    Write-Step "Rechecking public static asset graph after repair"
    $publicAssetsAfter = Test-StaticAssetGraph "public_static_assets_after" "https://lyraos.org/" $TimeoutSeconds
    Write-CheckResult $publicAssetsAfter
    if (-not $publicAssetsAfter.Ok) {
        throw "public static asset graph remains unhealthy after repair: $($publicAssetsAfter.Error)"
    }
    Write-Host "Static assets referenced by public HTML: $($publicAssetsAfter.AssetCount)"

    Ensure-OpenClawOperatorRelay $repoRoot ([bool]$SkipRelay)

    Write-Host "Runtime repaired and clean."
    exit 0
} catch {
    Write-Host "WATCHDOG_FAILED: $($_.Exception.Message)"
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
