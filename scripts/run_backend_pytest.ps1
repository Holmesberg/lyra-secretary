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

if (-not $PytestArgs -or $PytestArgs.Count -eq 0) {
  $PytestArgs = @("backend\tests")
}

$backendPath = Join-Path $repoRoot "backend"
$pathSeparator = [IO.Path]::PathSeparator
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
  $env:PYTHONPATH = $backendPath
} elseif (-not ($env:PYTHONPATH.Split($pathSeparator) -contains $backendPath)) {
  $env:PYTHONPATH = "$backendPath$pathSeparator$env:PYTHONPATH"
}

Write-Host "Backend pytest python: $python"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
Write-Host "pytest args: $($PytestArgs -join ' ')"

& $python -m pytest @PytestArgs
if ($LASTEXITCODE -ne 0) {
  throw "backend pytest failed with exit code $LASTEXITCODE"
}
