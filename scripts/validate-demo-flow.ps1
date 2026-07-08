# Validate UI flow + demo path (requires Postgres, backend :8000, frontend :3000).
# Usage: .\scripts\validate-demo-flow.ps1 [-SkipE2E] [-ApiBase "http://localhost:8000"]
param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$FrontendBase = "http://localhost:3000",
    [switch]$SkipE2E
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

. "$PSScriptRoot\ensure-docker-env.ps1"
Sync-FrontendApiEnv -ApiBase $ApiBase -ProjectRoot $Root

function Test-Endpoint {
    param([string]$Url, [string]$Label)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        Write-Host "OK  $Label ($($r.StatusCode))"
        return $true
    } catch {
        Write-Host "FAIL $Label - $($_.Exception.Message)"
        return $false
    }
}

Write-Host "=== Securi demo flow validation ===" -ForegroundColor Cyan

$backendOk = Test-Endpoint "$ApiBase/health" "Backend health"
$frontendOk = Test-Endpoint "$FrontendBase/login" "Frontend login page"
if (-not $backendOk -or -not $frontendOk) {
    Write-Host ""
    Write-Host "Start the stack first:" -ForegroundColor Yellow
    Write-Host "  docker compose -f docker-compose.dev.yml up -d"
    Write-Host "  cd backend; uvicorn app.main:app --reload --port 8000"
    Write-Host "  cd frontend; npx next dev --turbo -p 3000"
    exit 1
}

Write-Host ""
Write-Host "Running demo-setup..." -ForegroundColor Cyan
& "$PSScriptRoot\demo-setup.ps1" -ApiBase $ApiBase
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$public = Invoke-RestMethod -Uri "$ApiBase/api/v1/settings/public" -TimeoutSec 10
Write-Host ""
Write-Host "Public settings:" -ForegroundColor Cyan
Write-Host "  demo_mode=$($public.demo_mode)"
Write-Host "  exclude_simulated_from_dashboard=$($public.exclude_simulated_from_dashboard)"
Write-Host "  simulation_enabled=$($public.simulation_enabled)"

Write-Host ""
Write-Host "Typecheck frontend..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\..\frontend"
npx tsc --noEmit
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

if (-not $SkipE2E) {
    Write-Host ""
    Write-Host "Playwright smoke + lab flow (E2E_FULL_STACK=1)..." -ForegroundColor Cyan
    Push-Location "$PSScriptRoot\..\frontend"
    $env:E2E_FULL_STACK = "1"
    $env:PLAYWRIGHT_BASE_URL = $FrontendBase
    npx playwright test e2e/smoke.spec.ts e2e/lab-flow.spec.ts --workers=1
    $e2eExit = $LASTEXITCODE
    Pop-Location
    if ($e2eExit -ne 0) { exit $e2eExit }
}

Write-Host ""
Write-Host "=== Validation passed ===" -ForegroundColor Green
Write-Host "Manual walkthrough: docs/GUIDE_DEMO.md"
Write-Host 'Login: demo@securi.local / Demo1234!'
