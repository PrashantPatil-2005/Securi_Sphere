# Run Playwright E2E against a live local stack.
param(
    [string]$BaseUrl = "http://127.0.0.1:3000",
    [string]$Specs = "e2e/smoke.spec.ts e2e/threat-scores.spec.ts e2e/maintenance-flow.spec.ts e2e/intel-crud.spec.ts e2e/offense-promotion.spec.ts"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

. "$Root\scripts\ensure-docker-env.ps1"
$api = Resolve-ApiBase -ProjectRoot $Root
if (-not (Test-ApiReachable $api)) {
    Write-Host "API not reachable at $api - start with .\scripts\dev-windows.ps1"
    exit 1
}

Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm install }

$env:E2E_FULL_STACK = "1"
$env:PLAYWRIGHT_BASE_URL = $BaseUrl

Write-Host "==> Playwright E2E ($Specs)"
Write-Host "    API: $api"
Write-Host "    UI:  $BaseUrl"

$specList = $Specs -split '\s+'
npx playwright test @specList
exit $LASTEXITCODE
