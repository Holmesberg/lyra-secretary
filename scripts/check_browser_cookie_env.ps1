param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("alinassersabry", "asabryhafez", "holmesberg", "moriarty")]
  [string]$Account
)

$ErrorActionPreference = "Stop"

$envNames = @{
  "alinassersabry" = "LYRA_COOKIE_ALINASSERSABRY"
  "asabryhafez" = "LYRA_COOKIE_ASABRYHAFEZ"
  "holmesberg" = "LYRA_COOKIE_HOLMESBERG"
  "moriarty" = "LYRA_COOKIE_MORIARTY"
}

$envName = $envNames[$Account]
if ([string]::IsNullOrWhiteSpace($envName)) {
  throw "Unknown account: $Account"
}

$userValue = [Environment]::GetEnvironmentVariable($envName, "User")
if ($null -eq $userValue) { $userValue = "" }

$registryValue = ""
$registryItem = Get-ItemProperty -Path "HKCU:\Environment" -Name $envName -ErrorAction SilentlyContinue
if ($null -ne $registryItem) {
  $registryValue = $registryItem.$envName
  if ($null -eq $registryValue) { $registryValue = "" }
}

$processValue = [Environment]::GetEnvironmentVariable($envName, "Process")
if ($null -eq $processValue) { $processValue = "" }

$consistent = ($userValue -eq $registryValue) -and (
  [string]::IsNullOrEmpty($processValue) -or $processValue -eq $userValue
)

[pscustomobject]@{
  account = $Account
  env_name = $envName
  user_env_length = $userValue.Length
  registry_length = $registryValue.Length
  process_env_length = $processValue.Length
  consistent = $consistent
} | ConvertTo-Json -Depth 3
