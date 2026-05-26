param(
    [string[]]$Paths = @()
)

$ErrorActionPreference = "Stop"

Write-Host "## Git Hygiene Summary"
Write-Host ""

$branch = git branch --show-current
$head = git log -1 --oneline

Write-Host "Branch: $branch"
Write-Host "HEAD:   $head"
Write-Host ""

Write-Host "### Dirty Worktree"
$status = git status --short
if ($status) {
    $status | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "clean"
}

Write-Host ""
Write-Host "### Task-Scoped Paths"
if ($Paths.Count -gt 0) {
    foreach ($path in $Paths) {
        Write-Host "- $path"
    }

    Write-Host ""
    Write-Host "### Git Status For Task-Scoped Paths"
    git status --short -- @Paths

    Write-Host ""
    Write-Host "### Diffstat For Task-Scoped Paths"
    git diff --stat -- @Paths
} else {
    Write-Host "not provided"
}

Write-Host ""
Write-Host "### Final-Response Checklist"
Write-Host "- mention dirty worktree status"
Write-Host "- separate changes made this turn from pre-existing/unrelated changes"
Write-Host "- list files intentionally changed"
Write-Host "- list verification run and blockers"
Write-Host "- say whether anything was not committed/pushed"
