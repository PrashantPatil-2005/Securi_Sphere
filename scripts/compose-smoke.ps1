# Bring up CI compose stack and verify API health (Windows).
param(
    [string]$PostgresPassword = "smokepass",
    [string]$JwtSecret = "ci-smoke-test-secret-key-minimum-length"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:POSTGRES_PASSWORD = $PostgresPassword
$env:JWT_SECRET = $JwtSecret

try {
    Write-Host "==> Starting compose CI smoke stack"
    docker compose -f docker-compose.ci.yml up -d --build --wait
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    Write-Host "==> Checking liveness"
    $live = Invoke-RestMethod -Uri "http://localhost:8000/health/live"
    if (-not $live.status) { throw "liveness check failed" }

    Write-Host "==> Checking readiness"
    $ready = Invoke-RestMethod -Uri "http://localhost:8000/health/ready"
    if (-not $ready.status) { throw "readiness check failed" }

    Write-Host "==> Checking public settings"
    $settings = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/settings/public"
    if (-not $settings.environment) { throw "settings check failed" }

    Write-Host "Compose smoke test passed."
}
finally {
    docker compose -f docker-compose.ci.yml down -v --remove-orphans 2>$null
}
