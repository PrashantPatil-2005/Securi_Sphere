# Start Postgres + Redis for native dev (backend/frontend run on host).
param(
    [switch]$WithOpenSearch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. "$PSScriptRoot\ensure-docker-env.ps1"
Ensure-DockerEnv | Out-Null

if ($WithOpenSearch) {
    Write-Host "==> Starting Postgres, Redis, OpenSearch"
    docker compose -f docker-compose.dev.yml -f docker-compose.opensearch-dev.yml up -d
} else {
    Write-Host "==> Starting Postgres + Redis"
    docker compose -f docker-compose.dev.yml up -d
}

Write-Host "Waiting for Postgres..."
$max = 30
for ($i = 0; $i -lt $max; $i++) {
    docker exec securi-postgres pg_isready -U securi -d securi 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
}
if ($LASTEXITCODE -ne 0) { throw "Postgres did not become ready" }

Write-Host "Infrastructure ready."
if ($WithOpenSearch) {
    Write-Host "  OpenSearch: http://localhost:9200"
    Write-Host "  Set in backend/.env: OPENSEARCH_URL=http://localhost:9200 SEARCH_BACKEND=opensearch"
}
Write-Host "  Next: .\scripts\dev-windows.ps1  (or restart backend if already running)"
