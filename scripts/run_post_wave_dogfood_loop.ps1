param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",

  [ValidateSet("quick", "standard", "full", "chaos")]
  [string]$Mode = "standard",

  [string]$WaveName = "unnamed-wave",

  [switch]$IncludeMutable,

  [switch]$IncludeProductLoop,

  [switch]$IncludeCalendarTableMutation,

  [switch]$IncludeInsightsStates,

  [switch]$NoMutable,

  [switch]$IncludeCiCdProof,

  [switch]$CiCdFailOnUnsuccessful,

  [string]$CiCdWorkflow = "CI",

  [int]$LocalCurrentPort = 3013,

  [switch]$ProxyApi
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repoRoot ".venv311\Scripts\python.exe"
$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runStartedAt = Get-Date
$safeWaveName = ($WaveName -replace "[^A-Za-z0-9_.-]", "-").Trim("-")
if ([string]::IsNullOrWhiteSpace($safeWaveName)) {
  $safeWaveName = "unnamed-wave"
}
$runId = "$runStamp-$safeWaveName-$Mode-$Topology"
$outDir = Join-Path $repoRoot "tmp\post-wave-dogfood\$runId"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$mutableRequested = (
  [bool]$IncludeMutable `
  -or [bool]$IncludeProductLoop `
  -or [bool]$IncludeCalendarTableMutation
) -and -not [bool]$NoMutable -and $Mode -ne "quick"
if ([bool]$IncludeMutable -and [bool]$NoMutable) {
  throw "Use either -IncludeMutable or -NoMutable, not both."
}
if ([bool]$IncludeProductLoop -and $Mode -eq "quick") {
  throw "-IncludeProductLoop requires Mode standard, full, or chaos."
}
if ([bool]$IncludeCalendarTableMutation -and $Mode -eq "quick") {
  throw "-IncludeCalendarTableMutation requires Mode standard, full, or chaos."
}
if ([bool]$IncludeCalendarTableMutation -and $Topology -eq "public") {
  throw "-IncludeCalendarTableMutation is local-only until hosted-public mutable cleanup is explicitly approved."
}
$useProxyApi = [bool]$ProxyApi -or $Topology -eq "local-current"

$summary = [System.Collections.Generic.List[object]]::new()

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Body
  )

  Write-Host ""
  Write-Host "==> $Name"
  $started = Get-Date
  & $Body
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
  $durationMs = [int]((Get-Date) - $started).TotalMilliseconds
  $summary.Add([pscustomobject]@{
    step = $Name
    duration_ms = $durationMs
  }) | Out-Null
}

function Invoke-CheckedScript {
  param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,
    [string[]]$ScriptArgs = @()
  )
  & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @ScriptArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$ScriptPath failed with exit code $LASTEXITCODE"
  }
}

function Get-FrontendOriginForTopology {
  if ($Topology -eq "public") {
    return "https://lyraos.org"
  }
  if ($Topology -eq "local-current") {
    return "http://localhost:$LocalCurrentPort"
  }
  return "http://localhost:3000"
}

function Get-ApiOriginForTopology {
  if ($Topology -eq "public") {
    return "https://api.lyraos.org"
  }
  return "http://localhost:8000"
}

function Get-WrappedTopologyArgs {
  $args = @("-Topology", $Topology)
  if ($Topology -eq "local-current") {
    $args += @("-LocalCurrentPort", [string]$LocalCurrentPort)
    if ($useProxyApi) {
      $args += "-ProxyApi"
    }
  }
  return $args
}

function Get-NodeTopologyArgs {
  $args = @("--topology", $Topology)
  if ($Topology -eq "local-current") {
    $args += @(
      "--frontend", (Get-FrontendOriginForTopology),
      "--api", (Get-ApiOriginForTopology),
      "--nextauth", (Get-FrontendOriginForTopology)
    )
    if ($useProxyApi) {
      $args += "--proxy-api"
    }
  }
  return $args
}

function Assert-Cookie {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Account
  )
  $cookieJson = Invoke-CheckedScript `
    -ScriptPath ".\scripts\check_browser_cookie_env.ps1" `
    -ScriptArgs @("-Account", $Account)
  $cookieText = ($cookieJson -join "`n")
  $cookie = $cookieText | ConvertFrom-Json
  if (-not $cookie.consistent) {
    throw "$($cookie.env_name) is inconsistent across user/registry/process env."
  }
  if ([int]$cookie.user_env_length -lt 100 -or [int]$cookie.registry_length -lt 100) {
    throw "$($cookie.env_name) is missing or too short. Run save_browser_cookie_from_clipboard.ps1 for $Account."
  }
  Write-Host $cookieText
}

function Convert-ToRepoRelativePath {
  param([AllowNull()][string]$PathValue)
  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    return $null
  }
  try {
    $resolvedPath = (Resolve-Path $PathValue -ErrorAction Stop).Path
    $rootPath = (Resolve-Path $repoRoot -ErrorAction Stop).Path.TrimEnd("\", "/")
    if ($resolvedPath.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $resolvedPath.Substring($rootPath.Length).TrimStart("\", "/")
    }
    return $resolvedPath
  } catch {
    return $PathValue
  }
}

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$PathValue)
  if (-not (Test-Path $PathValue)) {
    return $null
  }
  try {
    return Get-Content -Raw -Path $PathValue | ConvertFrom-Json
  } catch {
    return [pscustomobject]@{
      ok = $false
      error = "json_parse_failed"
      detail = $_.Exception.Message
      path = Convert-ToRepoRelativePath $PathValue
    }
  }
}

function Get-FirstValue {
  param([object[]]$Values)
  foreach ($value in $Values) {
    if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) {
      return $value
    }
  }
  return $null
}

function Get-LastNonNullValue {
  param([object[]]$Values)
  $last = $null
  foreach ($value in $Values) {
    if ($null -ne $value) {
      $last = $value
    }
  }
  return $last
}

function Get-NestedResultFiles {
  param([object]$Artifacts)

  $dirs = @()
  foreach ($bucketName in @(
    "operator_readonly_stress",
    "browser_smoke",
    "product_loop",
    "calendar_table_mutation",
    "insights_states"
  )) {
    $bucket = $Artifacts.$bucketName
    if ($null -ne $bucket) {
      $dirs += @($bucket)
    }
  }

  $dirs |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path $_) } |
    ForEach-Object {
      $resultPath = Join-Path $_ "result.json"
      if (Test-Path $resultPath) {
        $resultPath
      }
    } |
    Sort-Object -Unique
}

function Get-ResultSummary {
  param([Parameter(Mandatory = $true)][string]$ResultPath)

  $json = Read-JsonFile $ResultPath
  if ($null -eq $json) {
    return $null
  }

  $routes = @($json.routes)
  $routeWarnings = @(
    $routes |
      Where-Object { $null -ne $_ } |
      ForEach-Object {
        $route = $_
        @($route.warnings) |
          Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
          ForEach-Object {
            [pscustomobject]@{
              route = $route.route
              viewport = $route.viewport
              warning = $_
              duration_ms = $route.duration_ms
            }
          }
      }
  )

  $cleanupChecks = @(
    @($json.checks) |
      Where-Object { $_.name -match "(?i)cleanup" } |
      ForEach-Object {
        [pscustomobject]@{
          name = $_.name
          ok = [bool]$_.ok
        }
      }
  )
  $cleanupPresent = ($null -ne $json.cleanup) -or $cleanupChecks.Count -gt 0
  $cleanupTaskCount = 0
  $cleanupDeadlineCount = 0
  $cleanupNotificationCount = 0
  if ($null -ne $json.cleanup) {
    $cleanupTaskCount = @($json.cleanup.task_ids | Where-Object { $null -ne $_ }).Count
    $cleanupDeadlineCount = @($json.cleanup.deadline_ids | Where-Object { $null -ne $_ }).Count
    $cleanupNotificationCount = @($json.cleanup.notification_ids | Where-Object { $null -ne $_ }).Count
  }
  $cleanupOk = if (-not $cleanupPresent) {
    $null
  } elseif ($cleanupChecks.Count -gt 0) {
    -not [bool](@($cleanupChecks | Where-Object { -not $_.ok }).Count)
  } else {
    $true
  }

  [pscustomobject]@{
    path = Convert-ToRepoRelativePath $ResultPath
    ok = $json.ok
    user_ref = $json.user_ref
    topology = $json.topology
    frontend_origin = Get-FirstValue @($json.frontendOrigin, $json.frontend_origin)
    api_origin = Get-FirstValue @($json.apiOrigin, $json.api_origin)
    output_dir = Convert-ToRepoRelativePath (Get-FirstValue @($json.output_dir, $json.outDir))
    issues = @($json.issues)
    warnings = @($json.warnings)
    route_warnings = $routeWarnings
    count_diffs = @($json.count_diffs)
    route_count_diffs = @($json.route_count_diffs)
    dashboard_snapshot_diffs = @($json.dashboard_snapshot_diffs)
    implementation_green = $json.dashboard_after_snapshot.cohort_readiness.implementation_green
    exposure_without_render_count = $json.dashboard_after_snapshot.notification_lifecycle.exposure_without_render_count
    cleanup = [pscustomobject]@{
      present = $cleanupPresent
      ok = $cleanupOk
      checks = $cleanupChecks
      task_count = $cleanupTaskCount
      deadline_count = $cleanupDeadlineCount
      notification_count = $cleanupNotificationCount
    }
  }
}

function New-EvidenceManifest {
  param(
    [Parameter(Mandatory = $true)][object]$Artifacts,
    [Parameter(Mandatory = $true)][string]$TopologyProofPath,
    [Parameter(Mandatory = $true)][bool]$MutableRequested
  )

  $topologyProof = Read-JsonFile $TopologyProofPath
  $nestedResults = @(
    Get-NestedResultFiles -Artifacts $Artifacts |
      ForEach-Object { Get-ResultSummary -ResultPath $_ } |
      Where-Object { $null -ne $_ }
  )
  $nestedIssues = @(
    $nestedResults |
      ForEach-Object {
        $result = $_
        @($result.issues) |
          Where-Object { $null -ne $_ } |
          ForEach-Object {
            [pscustomobject]@{
              source = $result.path
              issue = $_
            }
          }
      }
  )
  $nestedWarnings = @(
    $nestedResults |
      ForEach-Object {
        $result = $_
        @($result.warnings) |
          Where-Object { $null -ne $_ } |
          ForEach-Object {
            [pscustomobject]@{
              source = $result.path
              warning = $_
            }
          }
        @($result.route_warnings) |
          Where-Object { $null -ne $_ } |
          ForEach-Object {
            [pscustomobject]@{
              source = $result.path
              warning = $_
            }
          }
      }
  )
  $failedResults = @($nestedResults | Where-Object { $_.ok -eq $false })
  $cleanupSummaries = @($nestedResults | Where-Object { $_.cleanup.present })
  $cleanupOk = if (-not $MutableRequested) {
    $null
  } elseif ($cleanupSummaries.Count -eq 0) {
    $false
  } else {
    -not [bool](@($cleanupSummaries | Where-Object { $_.cleanup.ok -ne $true }).Count)
  }

  $operatorSummaries = @(
    $nestedResults |
      Where-Object {
        $_.path -like "*operator-readonly-stress*" -or
        $null -ne $_.implementation_green -or
        $null -ne $_.exposure_without_render_count
      }
  )

  [pscustomobject]@{
    ok = (
      ($null -ne $topologyProof -and $topologyProof.ok -eq $true) -and
      $failedResults.Count -eq 0 -and
      (-not $MutableRequested -or $cleanupOk -eq $true)
    )
    classification = if ($null -ne $topologyProof -and $topologyProof.ok -ne $true) {
      $topologyProof.classification
    } elseif ($failedResults.Count -gt 0) {
      "product_or_verifier_failure"
    } elseif ($MutableRequested -and $cleanupOk -ne $true) {
      "measurement_cleanup_failure"
    } else {
      "standard_wave_proof_passed"
    }
    topology_proof_path = Convert-ToRepoRelativePath $TopologyProofPath
    topology_proof = $topologyProof
    nested_result_count = $nestedResults.Count
    failed_results = $failedResults
    nested_issues = $nestedIssues
    nested_warnings = $nestedWarnings
    cleanup = [pscustomobject]@{
      required = $MutableRequested
      ok = $cleanupOk
      summaries = @($cleanupSummaries | ForEach-Object { $_.cleanup })
    }
    operator = [pscustomobject]@{
      summaries = $operatorSummaries
      implementation_green = Get-LastNonNullValue @($operatorSummaries | ForEach-Object { $_.implementation_green })
      exposure_without_render_count = Get-LastNonNullValue @($operatorSummaries | ForEach-Object { $_.exposure_without_render_count })
    }
  }
}

$transcriptPath = Join-Path $outDir "transcript.txt"
Start-Transcript -Path $transcriptPath -Force | Out-Null

Push-Location $repoRoot
try {
  Write-Host "Post-wave dogfood loop"
  Write-Host "Wave: $WaveName"
  Write-Host "Mode: $Mode"
  Write-Host "Topology: $Topology"
  Write-Host "Mutable: $mutableRequested"
  Write-Host "Out: $outDir"

  $commitSha = (git rev-parse --short HEAD).Trim()
  $fullCommitSha = (git rev-parse HEAD).Trim()
  $branchName = (git branch --show-current).Trim()
  $ciCdProofPath = Join-Path $outDir "ci_cd_proof.json"
  $topologyProofPath = Join-Path $outDir "topology_proof.json"

  Invoke-Step "cookie check: operator" {
    Assert-Cookie -Account "alinassersabry"
  }

  Invoke-Step "cookie check: Holmesberg non-operator account" {
    Assert-Cookie -Account "holmesberg"
  }

  if ($Mode -eq "quick") {
    Invoke-Step "git diff check" {
      git diff --check
    }

    Invoke-Step "runtime topology verifier" {
      $env:LYRA_FRONTEND_ORIGIN = Get-FrontendOriginForTopology
      $env:LYRA_API_ORIGIN = Get-ApiOriginForTopology
      $topologyArgs = Get-NodeTopologyArgs
      $topologyArgs += @("--out-file", $topologyProofPath)
      node scripts\verify_runtime_topology.mjs @topologyArgs
    }

    Invoke-Step "multi-account browser smoke" {
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\run_multi_account_browser_smoke.ps1" `
        -ScriptArgs (Get-WrappedTopologyArgs)
    }

    Invoke-Step "operator read-only browser stress" {
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
        -ScriptArgs (Get-WrappedTopologyArgs)
    }

    if ([bool]$IncludeInsightsStates) {
      Invoke-Step "Insights forced-state browser dogfood" {
        $frontend = Get-FrontendOriginForTopology
        $api = Get-ApiOriginForTopology
        $env:LYRA_COOKIE_HOLMESBERG = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_HOLMESBERG", "User")
        node scripts\browser_insights_states_dogfood.mjs --frontend $frontend --api $api
      }
    }
  } else {
    $stackArgs = @("-Topology", $Topology)
    if ($Topology -eq "local-current") {
      $stackArgs += @("-LocalCurrentPort", [string]$LocalCurrentPort)
    }
    if ($mutableRequested) {
      $stackArgs += "-IncludeMutable"
    }
    if ($Mode -eq "standard") {
      $stackArgs += "-SkipBackendFull"
    }

    Invoke-Step "S1C verification stack" {
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\run_s1c_verification_stack.ps1" `
        -ScriptArgs $stackArgs
    }

    Invoke-Step "runtime topology proof manifest" {
      $env:LYRA_FRONTEND_ORIGIN = Get-FrontendOriginForTopology
      $env:LYRA_API_ORIGIN = Get-ApiOriginForTopology
      $topologyArgs = Get-NodeTopologyArgs
      $topologyArgs += @("--out-file", $topologyProofPath)
      node scripts\verify_runtime_topology.mjs @topologyArgs
    }

    if ([bool]$IncludeInsightsStates) {
      Invoke-Step "Insights forced-state browser dogfood" {
        $frontend = Get-FrontendOriginForTopology
        $api = Get-ApiOriginForTopology
        $env:LYRA_COOKIE_HOLMESBERG = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_HOLMESBERG", "User")
        node scripts\browser_insights_states_dogfood.mjs --frontend $frontend --api $api
      }
    }

    if ([bool]$IncludeCalendarTableMutation) {
      Invoke-Step "Holmesberg calendar/table mutation browser dogfood" {
        $calendarTableArgs = @("-Topology", $Topology, "-RunId", $runId, "-OutDir", (Join-Path $outDir "calendar-table-mutation"))
        if ($Topology -eq "local-current") {
          $calendarTableArgs += @("-LocalCurrentPort", [string]$LocalCurrentPort, "-ProxyApi", "-AssumeLocalFrontendReady")
        }
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_calendar_table_mutation_dogfood.ps1" `
          -ScriptArgs $calendarTableArgs
      }
    }

    if ($mutableRequested) {
      Invoke-Step "operator read-only browser stress after mutable pass" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
          -ScriptArgs (Get-WrappedTopologyArgs)
      }
    }

    if ([bool]$IncludeProductLoop) {
      Invoke-Step "Holmesberg full product-loop browser dogfood" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_holmesberg_product_loop_dogfood.ps1" `
          -ScriptArgs (@("-RunId", $runId, "-OutDir", (Join-Path $outDir "holmesberg-product-loop")) + (Get-WrappedTopologyArgs))
      }

      Invoke-Step "operator read-only browser stress after product-loop dogfood" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
          -ScriptArgs (Get-WrappedTopologyArgs)
      }
    }

    if ($Mode -eq "chaos" -and $mutableRequested) {
      Invoke-Step "Holmesberg mutable browser smoke repeat" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_holmesberg_mutable_browser_smoke.ps1" `
          -ScriptArgs (Get-WrappedTopologyArgs)
      }

      Invoke-Step "operator read-only browser stress after chaos repeat" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
          -ScriptArgs (Get-WrappedTopologyArgs)
      }
    }
  }

  if ([bool]$IncludeCiCdProof) {
    Invoke-Step "CI/CD proof collection" {
      $ciArgs = @(
        "-Branch", $branchName,
        "-HeadSha", $fullCommitSha,
        "-Workflow", $CiCdWorkflow,
        "-OutFile", $ciCdProofPath
      )
      if ([bool]$CiCdFailOnUnsuccessful) {
        $ciArgs += "-FailOnUnsuccessful"
      }
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\collect_github_ci_cd_proof.ps1" `
        -ScriptArgs $ciArgs
    }
  }

  $artifacts = [pscustomobject]@{
    topology_proof = if (Test-Path $topologyProofPath) { $topologyProofPath } else { $null }
    operator_readonly_stress = @(
      Get-ChildItem -Path (Join-Path $repoRoot "tmp") -Directory -Filter "operator-readonly-stress-*" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $runStartedAt } |
        Sort-Object LastWriteTime |
        ForEach-Object { $_.FullName }
    )
    browser_smoke = @(
      Get-ChildItem -Path (Join-Path $repoRoot "tmp\browser-smoke") -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $runStartedAt } |
        Sort-Object LastWriteTime |
        ForEach-Object { $_.FullName }
    )
    product_loop = @(
      @(
        Get-ChildItem -Path (Join-Path $repoRoot "tmp\browser-product-loop") -Directory -ErrorAction SilentlyContinue |
          Where-Object { $_.LastWriteTime -ge $runStartedAt } |
          Sort-Object LastWriteTime |
          ForEach-Object { $_.FullName }
        $nestedProductLoop = Join-Path $outDir "holmesberg-product-loop"
        if (Test-Path $nestedProductLoop) {
          (Resolve-Path $nestedProductLoop).Path
        }
      )
    )
    calendar_table_mutation = @(
      @(
        Get-ChildItem -Path (Join-Path $repoRoot "tmp\browser-calendar-table-mutation") -Directory -ErrorAction SilentlyContinue |
          Where-Object { $_.LastWriteTime -ge $runStartedAt } |
          Sort-Object LastWriteTime |
          ForEach-Object { $_.FullName }
        $nestedCalendarTable = Join-Path $outDir "calendar-table-mutation"
        if (Test-Path $nestedCalendarTable) {
          (Resolve-Path $nestedCalendarTable).Path
        }
      )
    )
    insights_states = @(
      Get-ChildItem -Path (Join-Path $repoRoot "tmp\browser-insights-states") -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $runStartedAt } |
        Sort-Object LastWriteTime |
        ForEach-Object { $_.FullName }
    )
    ci_cd_proof = if (Test-Path $ciCdProofPath) { $ciCdProofPath } else { $null }
  }

  $evidenceManifest = New-EvidenceManifest `
    -Artifacts $artifacts `
    -TopologyProofPath $topologyProofPath `
    -MutableRequested $mutableRequested

  $result = [pscustomobject]@{
    ok = [bool]$evidenceManifest.ok
    commit = $commitSha
    branch = $branchName
    wave = $WaveName
    mode = $Mode
    topology = $Topology
    mutable_enabled = $mutableRequested
    output_dir = $outDir
    transcript = $transcriptPath
    artifacts = $artifacts
    evidence_manifest = $evidenceManifest
    steps = $summary
  }
  $result | ConvertTo-Json -Depth 6 | Tee-Object -FilePath (Join-Path $outDir "summary.json")
  if (-not $evidenceManifest.ok) {
    throw "post-wave evidence manifest failed: $($evidenceManifest.classification)"
  }
} finally {
  Pop-Location
  Stop-Transcript | Out-Null
}
