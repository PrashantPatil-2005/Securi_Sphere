# Lock down pilot after first admin account is created.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $Root ".env"

if (-not (Test-Path $envFile)) {
    throw ".env not found. Deploy first with deploy-windows-lan.ps1"
}

$content = Get-Content $envFile -Raw
$content = $content -replace "ALLOW_REGISTRATION=true", "ALLOW_REGISTRATION=false"
$content = $content -replace "ENABLE_SIMULATION=true", "ENABLE_SIMULATION=false"
Set-Content -Encoding utf8 $envFile $content
Copy-Item $envFile (Join-Path $Root "backend\.env") -Force

Write-Host "Updated .env: ALLOW_REGISTRATION=false, ENABLE_SIMULATION=false"
Write-Host "Restarting backend + worker..."
Set-Location $Root
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend worker

Write-Host "Pilot hardened. New user registration and simulation are disabled."
