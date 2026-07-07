# Prepare a live demo: admin user, demo host, optional attack simulation.
# Usage: .\scripts\demo-setup.ps1 [-ApiBase "http://localhost:8000"]
param(
    [string]$ApiBase = "",
    [string]$Email = "demo@securi.local",
    [string]$Password = "Demo1234!",
    [string]$HostName = "demo-server",
    [switch]$SkipSimulation
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

. "$PSScriptRoot\ensure-docker-env.ps1"

$preferredApi = $ApiBase
if (-not $preferredApi) {
    $envFile = Join-Path $Root "backend\.env"
    if (Test-Path $envFile) {
        $match = Select-String -Path $envFile -Pattern '^SERVER_URL=(.+)$' | Select-Object -First 1
        if ($match) { $preferredApi = $match.Matches[0].Groups[1].Value.Trim() }
    }
    if (-not $preferredApi) { $preferredApi = "http://localhost:8000" }
}

$ApiBase = Resolve-ApiBase -Preferred $preferredApi -ProjectRoot $Root
if ($ApiBase -ne $preferredApi) {
    Write-Host "Note: $preferredApi unreachable - using $ApiBase for setup"
}

$frontendUrl = $ApiBase -replace ':8000', ':3000'
$envFile = Join-Path $Root "backend\.env"
if (Test-Path $envFile) {
    $fe = Select-String -Path $envFile -Pattern '^FRONTEND_URL=(.+)$' | Select-Object -First 1
    if ($fe) { $frontendUrl = $fe.Matches[0].Groups[1].Value.Trim() }
}
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

Write-Host "Securi demo setup -> $ApiBase"

function Invoke-SecuriApi {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )
    $params = @{
        Uri = "$ApiBase$Path"
        Method = $Method
        WebSession = $session
        ContentType = "application/json"
    }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json) }
    return Invoke-RestMethod @params
}

try {
    Invoke-SecuriApi -Method POST -Path "/api/v1/auth/register" -Body @{
        email = $Email
        password = $Password
    }
    Write-Host "Registered $Email"
} catch {
    Write-Host "User may already exist - trying login..."
}

Invoke-SecuriApi -Method POST -Path "/api/v1/auth/login" -Body @{
    email = $Email
    password = $Password
} | Out-Null
Write-Host "Logged in as $Email"

$hostRes = Invoke-SecuriApi -Method POST -Path "/api/v1/hosts" -Body @{ name = $HostName }
$hostId = $hostRes.id
Write-Host "Created host: $HostName ($hostId)"

if (-not $SkipSimulation) {
    $null = Invoke-SecuriApi -Method POST -Path "/api/v1/simulation/run/multi_stage_attack?host_id=$hostId"
    Write-Host "Ran multi_stage_attack simulation on $HostName"
}

Write-Host ""
Write-Host "=== Demo ready ==="
Write-Host "  Dashboard: $frontendUrl"
Write-Host "  Email:    $Email"
Write-Host "  Password: $Password"
Write-Host ""
Write-Host "For dashboard charts to include simulated events during the demo, set:"
Write-Host "  EXCLUDE_SIMULATED_FROM_DASHBOARD=false"
Write-Host "Then restart the backend. After the demo, purge simulated data from Attack Lab."
