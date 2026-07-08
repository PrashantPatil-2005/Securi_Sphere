# Run backend tests (unit + integration). Requires Postgres from start-infra.ps1.
param(
    [string]$Path = "tests",
    [switch]$IntegrationOnly,
    [switch]$Quick,
    [switch]$SearchGate
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location "$Root\backend"

. "$Root\scripts\ensure-docker-env.ps1"
Ensure-DockerEnv | Out-Null

if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\pip install -r requirements.txt -q 2>$null
if ($LASTEXITCODE -ne 0) {
    .\venv\Scripts\pip install -r requirements.txt
}

if ($SearchGate) {
    $Path = "tests/test_opensearch_scale.py tests/test_siem_opensearch.py tests/integration/test_system_admin_api.py tests/integration/test_search.py"
} elseif ($IntegrationOnly) {
    $Path = "tests/integration"
} elseif ($Quick) {
    $Path = "tests/test_public_settings.py tests/test_read_replica.py tests/test_analytics_materialized_views.py tests/test_db_pool.py tests/test_opensearch_scale.py tests/test_siem_opensearch.py tests/integration/test_notifications_settings_test.py tests/integration/test_maintenance_api.py tests/integration/test_system_admin_api.py tests/integration/test_search.py"
}

Write-Host "==> pytest $Path"
.\venv\Scripts\python -m pytest $Path.Split(" ") -q --tb=short
exit $LASTEXITCODE
