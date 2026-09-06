# Write SERVER_URL / FRONTEND_URL from the current LAN IPv4 (or -LanIp).
# Usage:
#   .\scripts\sync-lan-urls.ps1
#   .\scripts\sync-lan-urls.ps1 -LanIp 10.0.0.12
param(
    [string]$LanIp = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\lan-url.ps1"

$ip = Get-PreferredLanIPv4 -LanIp $LanIp
$result = Set-SecuriLanUrls -ProjectRoot $Root -LanIp $ip -PublishOnAllInterfaces
Write-Host "Updated LAN URLs:"
Write-Host "  SERVER_URL=$($result.ServerUrl)"
Write-Host "  FRONTEND_URL=$($result.FrontendUrl)"
Write-Host "Restart the API so enrollment install commands pick up SERVER_URL."
Write-Host "Bind remains 0.0.0.0:8000; agents must use $($result.ServerUrl) not localhost."
