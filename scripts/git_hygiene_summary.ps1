param(
    [string[]]$Paths = @(),
    [switch]$ForPush,
    [switch]$ForMerge,
    [switch]$FailOnWarnings,
    [string]$BaseRef = "origin/main"
)

$ErrorActionPreference = "Stop"

$blockers = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

function Add-Blocker([string]$Message) {
    [void]$blockers.Add($Message)
}

function Add-Warning([string]$Message) {
    [void]$warnings.Add($Message)
}

function Normalize-PathForGit([string]$Path) {
    return ($Path -replace "\\", "/").Trim()
}

function Path-IsArtifact([string]$Path) {
    $normalized = Normalize-PathForGit $Path
    if ($normalized -match "(^|/)\.env\.example$") {
        return $false
    }
    $patterns = @(
        "^tmp/",
        "^frontend/\.next/",
        "^frontend/out/",
        "^node_modules/",
        "^backend/\.pytest_cache/",
        "^\.pytest_cache/",
        "(^|/)\.env($|\.)",
        "\.log$",
        "\.sqlite$",
        "\.sqlite3$",
        "\.db$",
        "\.bak$",
        "\.tmp$"
    )

    foreach ($pattern in $patterns) {
        if ($normalized -match $pattern) {
            return $true
        }
    }
    return $false
}

function Path-IsGeneratedMedia([string]$Path) {
    $normalized = Normalize-PathForGit $Path
    return $normalized -match "\.(png|jpg|jpeg|webp|gif|mp4|mov|pptx|xlsx)$"
}

function Get-PathFromStatusLine([string]$Line) {
    if (-not $Line -or $Line.Length -lt 4) {
        return $null
    }
    $path = $Line.Substring(3).Trim()
    if ($path -match " -> ") {
        $parts = $path -split " -> "
        $path = $parts[$parts.Length - 1].Trim()
    }
    return Normalize-PathForGit $path
}

function Write-List([string]$EmptyText, [string[]]$Items) {
    if ($Items -and $Items.Count -gt 0) {
        foreach ($item in $Items) {
            Write-Host "- $item"
        }
    } else {
        Write-Host $EmptyText
    }
}

Write-Host "## Git Hygiene Summary"
Write-Host ""

$branch = git branch --show-current
$head = git log -1 --oneline
$upstream = ""
try {
    $upstream = git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
} catch {
    $upstream = ""
}

Write-Host "Branch:  $branch"
Write-Host "HEAD:    $head"
if ($upstream) {
    Write-Host "Upstream: $upstream"
} else {
    Add-Warning "No upstream branch is configured."
    Write-Host "Upstream: none"
}
Write-Host "Mode:    $(if ($ForMerge) { "merge gate" } elseif ($ForPush) { "push gate" } else { "summary" })"
Write-Host ""

$statusLines = @(git status --short)
$statusPaths = @($statusLines | ForEach-Object { Get-PathFromStatusLine $_ } | Where-Object { $_ })

Write-Host "### Dirty Worktree"
if ($statusLines.Count -gt 0) {
    $statusLines | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "clean"
}

if ($Paths.Count -eq 0 -and $ForPush) {
    Add-Warning "No task-scoped paths were provided. Pass -Paths for push gates."
}

$dirtyArtifacts = @($statusPaths | Where-Object { Path-IsArtifact $_ })
$dirtyGeneratedMedia = @($statusPaths | Where-Object { Path-IsGeneratedMedia $_ })

if ($dirtyArtifacts.Count -gt 0) {
    $message = "Dirty artifact paths detected: $($dirtyArtifacts -join ', ')"
    if ($ForPush -or $ForMerge) {
        Add-Blocker $message
    } else {
        Add-Warning $message
    }
}

if ($dirtyGeneratedMedia.Count -gt 0) {
    $message = "Dirty generated/binary media paths detected: $($dirtyGeneratedMedia -join ', ')"
    if ($ForPush -or $ForMerge) {
        Add-Blocker $message
    } else {
        Add-Warning $message
    }
}

Write-Host ""
Write-Host "### Task-Scoped Paths"
if ($Paths.Count -gt 0) {
    foreach ($path in $Paths) {
        Write-Host "- $path"
    }

    Write-Host ""
    Write-Host "### Git Status For Task-Scoped Paths"
    git status --short -- $Paths

    Write-Host ""
    Write-Host "### Diffstat For Task-Scoped Paths"
    Write-Host "unstaged:"
    git diff --stat -- $Paths
    Write-Host "staged:"
    git diff --cached --stat -- $Paths
} else {
    Write-Host "not provided"
}

Write-Host ""
Write-Host "### Staged Files"
$stagedFiles = @(git diff --cached --name-only | ForEach-Object { Normalize-PathForGit $_ })
Write-List "none" $stagedFiles

if ($stagedFiles.Count -gt 0) {
    $stagedArtifacts = @($stagedFiles | Where-Object { Path-IsArtifact $_ })
    $stagedGeneratedMedia = @($stagedFiles | Where-Object { Path-IsGeneratedMedia $_ })
    if ($stagedArtifacts.Count -gt 0) {
        Add-Blocker "Staged artifact paths detected: $($stagedArtifacts -join ', ')"
    }
    if ($stagedGeneratedMedia.Count -gt 0) {
        Add-Blocker "Staged generated/binary media paths detected: $($stagedGeneratedMedia -join ', ')"
    }
}

Write-Host ""
Write-Host "### Changed Files In Working Tree"
Write-List "none" $statusPaths

if ($ForMerge) {
    Write-Host ""
    Write-Host "### PR Diff Against $BaseRef"
    $baseExists = $true
    try {
        git rev-parse --verify $BaseRef 1>$null 2>$null
    } catch {
        $baseExists = $false
    }

    if ($baseExists) {
        $prFiles = @(git diff --name-only "$BaseRef...HEAD" | ForEach-Object { Normalize-PathForGit $_ })
        $prFileCount = $prFiles.Count
        Write-Host "changed files: $prFileCount"
        git diff --stat "$BaseRef...HEAD"

        $prArtifacts = @($prFiles | Where-Object { Path-IsArtifact $_ })
        $prGeneratedMedia = @($prFiles | Where-Object { Path-IsGeneratedMedia $_ })
        $migrationFiles = @($prFiles | Where-Object { $_ -match "^backend/alembic/versions/" })

        if ($prArtifacts.Count -gt 0) {
            Add-Blocker "PR diff includes artifact paths: $($prArtifacts -join ', ')"
        }
        if ($prGeneratedMedia.Count -gt 0) {
            Add-Warning "PR diff includes generated/binary media paths; confirm intentional: $($prGeneratedMedia -join ', ')"
        }
        if ($migrationFiles.Count -gt 0) {
            Add-Warning "Alembic migrations changed; confirm revision ordering and upgrade path: $($migrationFiles -join ', ')"
        }
        if ($prFileCount -gt 150) {
            Add-Warning "Large PR diff ($prFileCount files). Prefer merging this checkpoint before starting the next wave."
        }
    } else {
        Add-Blocker "Base ref '$BaseRef' is not available locally. Fetch it before merge hygiene."
        Write-Host "base ref unavailable"
    }
}

Write-Host ""
Write-Host "### Required Verification Report"
Write-Host "Git hygiene:"
Write-Host "- branch: $branch"
Write-Host "- worktree: $(if ($statusLines.Count -gt 0) { "dirty" } else { "clean" })"
Write-Host "- committed files: <list explicit files or 'none yet'>"
Write-Host "- tests: <commands and results>"
Write-Host "- browser verification: <screenshots/result paths or 'not applicable'>"
Write-Host "- CI: <actual PR check status after push or 'not pushed'>"
Write-Host "- artifacts intentionally kept: <list or 'none'>"
Write-Host "- artifacts left local only: <list or 'none'>"
Write-Host "- merge risk: <clean/conflict risk/hot files>"

Write-Host ""
Write-Host "### Warnings"
Write-List "none" $warnings.ToArray()

Write-Host ""
Write-Host "### Blockers"
Write-List "none" $blockers.ToArray()

if ($blockers.Count -gt 0) {
    Write-Host ""
    Write-Host "Git hygiene gate: FAIL"
    exit 1
}

if ($FailOnWarnings -and $warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Git hygiene gate: FAIL warnings"
    exit 1
}

Write-Host ""
Write-Host "Git hygiene gate: PASS"
