param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv311\Scripts\python.exe"

if (Test-Path -LiteralPath $venvPython) {
  $python = $venvPython
} else {
  $pythonCommand = Get-Command python -ErrorAction Stop
  $python = $pythonCommand.Source
}

$backendPath = Join-Path $repoRoot "backend"

function Convert-BackendPytestArg {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Arg
  )

  # CI runs from ./backend with paths like tests/foo.py. Keep the local wrapper
  # equivalent even when callers pass repo-root paths such as backend\tests.
  if ($Arg -match '^(?i)backend[\\/]') {
    return ($Arg -replace '^(?i)backend[\\/]', '')
  }
  return $Arg
}

if (-not $PytestArgs -or $PytestArgs.Count -eq 0) {
  $PytestArgs = @("tests")
} else {
  $PytestArgs = @($PytestArgs | ForEach-Object { Convert-BackendPytestArg $_ })
}

$pathSeparator = [IO.Path]::PathSeparator
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
  $env:PYTHONPATH = $backendPath
} elseif (-not ($env:PYTHONPATH.Split($pathSeparator) -contains $backendPath)) {
  $env:PYTHONPATH = "$backendPath$pathSeparator$env:PYTHONPATH"
}

Write-Host "Backend pytest python: $python"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
Write-Host "pytest args: $($PytestArgs -join ' ')"

Push-Location $backendPath
try {
  & $python -m pytest @PytestArgs
  if ($LASTEXITCODE -ne 0) {
    throw "backend pytest failed with exit code $LASTEXITCODE"
  }
} finally {
  Pop-Location
}
