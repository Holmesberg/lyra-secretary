param(
    [switch]$ApprovedPublicRestart,
    [switch]$NoBuild,
    [switch]$SkipHostedCheck,
    [int]$WaitSeconds = 90
)

$ErrorActionPreference = "Stop"

if (-not $ApprovedPublicRestart) {
    throw "Public backend restart requires the explicit -ApprovedPublicRestart switch."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composePath = Join-Path $repoRoot "docker-compose.yml"
$publicImage = "lyra-backend-public:current"
$rollbackImage = "lyra-backend-public:previous"
$previousBuildId = $null
$hasRollbackImage = $false
$priorBuildEnv = $env:BACKEND_BUILD_ID

function Invoke-Docker([string[]]$Arguments, [string]$FailureMessage) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Wait-ForTopology([string]$Uri, [string]$ExpectedBuildId, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $last = $null
    do {
        try {
            $last = Invoke-RestMethod -Uri $Uri -Headers @{ Origin = "https://lyraos.org" } -TimeoutSec 5
            if ($last.build_id -eq $ExpectedBuildId) {
                return $last
            }
        } catch {
            $last = $_.Exception.Message
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    $detail = if ($last -is [string]) { $last } else { $last | ConvertTo-Json -Compress -Depth 5 }
    throw "Backend topology did not serve expected build id $ExpectedBuildId within ${TimeoutSeconds}s. Last result: $detail"
}

function Restore-PreviousBackend {
    if (-not $hasRollbackImage) {
        Write-Warning "No previous backend image is available for automatic rollback."
        return
    }
    Write-Warning "Restoring previous public backend image."
    Invoke-Docker @("image", "tag", $rollbackImage, $publicImage) "Could not restore the previous backend image tag."
    $env:BACKEND_BUILD_ID = if ($previousBuildId) { $previousBuildId } else { "rollback-unknown" }
    Invoke-Docker @("compose", "-f", $composePath, "up", "-d", "--no-build", "backend", "redis") "Could not restart the previous backend image."
    if ($previousBuildId) {
        $null = Wait-ForTopology "http://localhost:8000/v1/health/topology" $previousBuildId $WaitSeconds
    }
}

Push-Location $repoRoot
try {
    $dirty = @(git status --porcelain --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect Git status before public backend restart."
    }
    if ($dirty.Count -gt 0) {
        throw "Refusing to deploy the public backend from a dirty tracked or untracked tree."
    }

    $expectedBuildId = (git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $expectedBuildId) {
        throw "Could not resolve the expected backend build id."
    }

    try {
        $current = Invoke-RestMethod -Uri "http://localhost:8000/v1/health/topology" -Headers @{ Origin = "https://lyraos.org" } -TimeoutSec 5
        $previousBuildId = [string]$current.build_id
    } catch {
        $previousBuildId = $null
    }

    $containerId = [string](& docker compose -f $composePath ps -q backend)
    $containerId = $containerId.Trim()
    if ($containerId) {
        $runningImageId = [string](& docker inspect --format "{{.Image}}" $containerId)
        $runningImageId = $runningImageId.Trim()
        if ($LASTEXITCODE -eq 0 -and $runningImageId) {
            Invoke-Docker @("image", "tag", $runningImageId, $rollbackImage) "Could not preserve the running backend image for rollback."
            $hasRollbackImage = $true
        }
    } else {
        & docker image inspect $publicImage *> $null
        if ($LASTEXITCODE -eq 0) {
            Invoke-Docker @("image", "tag", $publicImage, $rollbackImage) "Could not preserve the current backend image for rollback."
            $hasRollbackImage = $true
        }
    }

    $env:BACKEND_BUILD_ID = $expectedBuildId
    if ($NoBuild) {
        $imageBuildId = [string](& docker image inspect --format "{{ index .Config.Labels `"org.lyraos.backend-build-id`" }}" $publicImage)
        $imageBuildId = $imageBuildId.Trim()
        if ($LASTEXITCODE -ne 0 -or $imageBuildId -ne $expectedBuildId) {
            throw "Existing backend image build id '$imageBuildId' does not match expected commit '$expectedBuildId'."
        }
    } else {
        Invoke-Docker @("compose", "-f", $composePath, "build", "backend") "Public backend image build failed; the running container was not replaced."
    }

    try {
        Invoke-Docker @("compose", "-f", $composePath, "up", "-d", "--no-build", "backend", "redis") "Public backend container swap failed."
        Invoke-Docker @("compose", "-f", $composePath, "exec", "-T", "backend", "alembic", "upgrade", "head") "Backend migration check failed."
        $local = Wait-ForTopology "http://localhost:8000/v1/health/topology" $expectedBuildId $WaitSeconds
        if (-not $SkipHostedCheck) {
            $null = Wait-ForTopology "https://api.lyraos.org/v1/health/topology" $expectedBuildId $WaitSeconds
        }
        Write-Host "Public backend serves build $($local.build_id)."
    } catch {
        Restore-PreviousBackend
        throw
    }
} finally {
    if ($null -eq $priorBuildEnv) {
        Remove-Item Env:BACKEND_BUILD_ID -ErrorAction SilentlyContinue
    } else {
        $env:BACKEND_BUILD_ID = $priorBuildEnv
    }
    Pop-Location
}
