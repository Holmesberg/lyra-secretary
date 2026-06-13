param(
    [switch]$NoRepair,
    [switch]$AllowFullBuild,
    [int]$TimeoutSeconds = 20,
    [string]$LogDir = ""
)

$ErrorActionPreference = "Stop"

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

    if ($publicOk) {
        Write-Step "Verifying public topology"
        node (Join-Path $repoRoot "scripts\verify_runtime_topology.mjs") --topology public --skip-browser
        if ($LASTEXITCODE -ne 0) {
            throw "public topology verification failed."
        }
        Write-Host "Runtime is clean."
        exit 0
    }

    if ($NoRepair) {
        throw "public runtime is unhealthy and repair is disabled."
    }

    if ($localOk) {
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

    Write-Host "Runtime repaired and clean."
    exit 0
} catch {
    Write-Host "WATCHDOG_FAILED: $($_.Exception.Message)"
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
