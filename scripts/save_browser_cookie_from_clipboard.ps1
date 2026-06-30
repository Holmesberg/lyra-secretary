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

function Get-NormalizedCookieValue {
  param([string]$Raw)

  $cookie = ($Raw -replace "^\s*cookie:\s*", "").Trim()
  if ([string]::IsNullOrWhiteSpace($cookie)) {
    throw "Clipboard is empty. Copy the VALUE of __Secure-next-auth.session-token first."
  }

  $match = [regex]::Match(
    $cookie,
    "(?:^|[\s;'\`"])(?:__Secure-next-auth\.session-token|next-auth\.session-token)=([^;'\`"\s]+)"
  )
  if ($match.Success) {
    $cookie = $match.Groups[1].Value.Trim()
  }

  # Chrome's cookie table often copies an ellipsized preview. Reject those.
  if ($cookie.Contains("...") -or $cookie.Contains([char]0x2026)) {
    throw "Cookie looks truncated. Open the cookie row and copy the full Value field, not the table preview."
  }

  if ($cookie.Length -lt 40) {
    throw "Cookie looks too short: length=$($cookie.Length). Copy the full VALUE of __Secure-next-auth.session-token."
  }
  if ($cookie.StartsWith("eyJ") -and (($cookie.ToCharArray() | Where-Object { $_ -eq "." }).Count -lt 4)) {
    throw "Cookie looks like a partial encrypted JWT/JWE: length=$($cookie.Length). Use Network -> any lyraos.org request -> Copy -> Copy as cURL, then rerun this script."
  }

  return $cookie
}

$name = $envNames[$Account]
$raw = Get-Clipboard -Raw
$cookie = Get-NormalizedCookieValue -Raw $raw

[Environment]::SetEnvironmentVariable($name, $cookie, "User")
Set-ItemProperty -Path "HKCU:\Environment" -Name $name -Value $cookie
Set-Item -Path "Env:$name" -Value $cookie

if ($cookie.Length -lt 300) {
  Write-Warning "Saved cookie is shorter than the operator JWT-style cookie. This can still be valid; run the browser smoke to confirm session resolution."
}
$userValue = [Environment]::GetEnvironmentVariable($name, "User")
$registryValue = (Get-ItemProperty -Path "HKCU:\Environment" -Name $name -ErrorAction Stop).$name
$processValue = (Get-Item -Path "Env:$name" -ErrorAction Stop).Value

"Saved $name length=$($cookie.Length) pairs=$((($cookie -split ';') | Where-Object { $_ -match '=' }).Count)"
"Verify user-env length=$($userValue.Length)"
"Verify registry length=$($registryValue.Length)"
"Verify process-env length=$($processValue.Length)"
