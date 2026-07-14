param(
  [string]$Branch = "",
  [string]$HeadSha = "",
  [string]$Workflow = "CI",
  [int]$Limit = 10,
  [string]$OutFile = "",
  [switch]$FailOnUnsuccessful
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Invoke-GhJson {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Arguments
  )

  $output = & gh @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "gh $($Arguments -join ' ') failed: $($output -join "`n")"
  }
  $text = ($output -join "`n").Trim()
  if ([string]::IsNullOrWhiteSpace($text)) {
    return $null
  }
  return $text | ConvertFrom-Json
}

Push-Location $repoRoot
try {
  if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = (git branch --show-current).Trim()
  }
  if ([string]::IsNullOrWhiteSpace($HeadSha)) {
    $HeadSha = (git rev-parse HEAD).Trim()
  }
  $shortHead = (git rev-parse --short $HeadSha).Trim()

  $proof = [ordered]@{
    ok = $false
    collected_at = (Get-Date).ToUniversalTime().ToString("o")
    branch = $Branch
    head_sha = $HeadSha
    short_head_sha = $shortHead
    workflow = $Workflow
    status = "not_collected"
    failure_classification = $null
    actions = [ordered]@{}
    pull_request = [ordered]@{}
  }

  try {
    $runsRaw = Invoke-GhJson -Arguments @(
      "run", "list",
      "--workflow", $Workflow,
      "--branch", $Branch,
      "--limit", [string]$Limit,
      "--json", "databaseId,workflowName,displayTitle,headSha,status,conclusion,event,createdAt,updatedAt,url"
    )
    $runs = @($runsRaw)
    $matchingRuns = @($runs | Where-Object { $_.headSha -eq $HeadSha })
    $selectedRun = $null
    if ($matchingRuns.Count -gt 0) {
      $selectedRun = $matchingRuns[0]
    } elseif ($runs.Count -gt 0) {
      $selectedRun = $runs[0]
    }

    $proof.actions = [ordered]@{
      recent_run_count = $runs.Count
      matching_head_run_count = $matchingRuns.Count
      selected_run = $selectedRun
      recent_runs = $runs
      selected_run_detail = $null
    }

    if ($null -eq $selectedRun) {
      $proof.status = "no_workflow_ran"
      $proof.failure_classification = "ci_cd_operations_bug"
    } else {
      $runDetail = Invoke-GhJson -Arguments @(
        "run", "view", [string]$selectedRun.databaseId,
        "--json", "databaseId,workflowName,status,conclusion,headSha,url,jobs,event,createdAt,updatedAt"
      )
      $proof.actions.selected_run_detail = $runDetail

      $isExactHead = $runDetail.headSha -eq $HeadSha
      if (-not $isExactHead) {
        $proof.status = "no_matching_run_for_head"
        $proof.failure_classification = "ci_cd_operations_bug"
      } elseif ($runDetail.status -ne "completed") {
        $proof.status = "ci_pending"
        $proof.failure_classification = "ci_cd_operations_bug"
      } elseif ($runDetail.conclusion -eq "success") {
        $proof.status = "ci_success"
        $proof.ok = $true
      } else {
        $proof.status = "ci_failed"
        $proof.failure_classification = "unclassified_ci_failure"
      }
    }
  } catch {
    $proof.status = "gh_actions_collection_failed"
    $proof.failure_classification = "ci_cd_operations_bug"
    $proof.actions = [ordered]@{
      error = $_.Exception.Message
    }
  }

  try {
    $prsRaw = Invoke-GhJson -Arguments @(
      "pr", "list",
      "--head", $Branch,
      "--json", "number,url,title,headRefName,headRefOid,state,isDraft,statusCheckRollup"
    )
    $prs = @($prsRaw)
    if ($prs.Count -eq 0) {
      $proof.pull_request = [ordered]@{
        status = "no_pr"
        prs = @()
      }
    } else {
      $selectedPr = $prs[0]
      $checks = $null
      try {
        $checks = Invoke-GhJson -Arguments @(
          "pr", "checks", [string]$selectedPr.number,
          "--json", "name,state,bucket,workflow,link,startedAt,completedAt"
        )
      } catch {
        $checks = [ordered]@{
          error = $_.Exception.Message
        }
      }
      $proof.pull_request = [ordered]@{
        status = "pr_found"
        selected_pr = $selectedPr
        checks = $checks
      }
    }
  } catch {
    $proof.pull_request = [ordered]@{
      status = "pr_collection_failed"
      failure_classification = "ci_cd_operations_bug"
      error = $_.Exception.Message
    }
  }

  $json = $proof | ConvertTo-Json -Depth 12
  if (-not [string]::IsNullOrWhiteSpace($OutFile)) {
    $outPath = if ([System.IO.Path]::IsPathRooted($OutFile)) {
      $OutFile
    } else {
      Join-Path $repoRoot $OutFile
    }
    $outParent = Split-Path -Parent $outPath
    if (-not [string]::IsNullOrWhiteSpace($outParent)) {
      New-Item -ItemType Directory -Force -Path $outParent | Out-Null
    }
    $json | Set-Content -Path $outPath -Encoding UTF8
  }
  Write-Output $json

  if ([bool]$FailOnUnsuccessful -and -not [bool]$proof.ok) {
    exit 1
  }
} finally {
  Pop-Location
}
