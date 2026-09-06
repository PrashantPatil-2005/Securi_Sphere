# Fail if SERVER_URL in .env points at an IPv4 that is not on this machine.
param(
    [string]$ServerUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\lan-url.ps1"

if (-not $ServerUrl) {
    foreach ($candidate in @(
            (Join-Path $Root "backend\.env"),
            (Join-Path $Root ".env")
        )) {
        if (Test-Path $candidate) {
            $line = Select-String -Path $candidate -Pattern '^SERVER_URL=(.+)$' | Select-Object -First 1
            if ($line) {
                $ServerUrl = $line.Matches[0].Groups[1].Value.Trim()
                break
            }
        }
    }
}

if (-not $ServerUrl) {
    throw "SERVER_URL is not set. Run .\scripts\sync-lan-urls.ps1 or pass -ServerUrl."
}

Assert-ServerUrlOnLocalInterface -ServerUrl $ServerUrl
Write-Host "SERVER_URL is valid on this host: $ServerUrl"
