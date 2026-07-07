# Run backend tests (unit + integration). Requires Postgres from start-infra.ps1.
param(
    [string]$Path = "tests",
    [switch]$IntegrationOnly,
    [switch]$Quick
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\backend"

. "$Root\scripts\ensure-docker-env.ps1"
Ensure-DockerEnv | Out-Null

if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\pip install -r requirements.txt -q

if ($IntegrationOnly) {
    $Path = "tests/integration"
} elseif ($Quick) {
    $Path = "tests/test_public_settings.py tests/integration/test_notifications_settings_test.py tests/integration/test_maintenance_api.py"
}

Write-Host "==> pytest $Path"
.\venv\Scripts\python -m pytest $Path.Split(" ") -q --tb=short
exit $LASTEXITCODE
