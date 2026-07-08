# Run Playwright E2E against a live local stack.
param(
    [string]$BaseUrl = "",
    [string]$ApiBase = "",
    [switch]$GoldenPathOnly,
    [switch]$SkipEnvSync
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

. "$Root\scripts\ensure-docker-env.ps1"
$api = Resolve-ApiBase -Preferred $ApiBase -ProjectRoot $Root
if (-not (Test-ApiReachable $api)) {
    Write-Host "API not reachable at $api - start with .\scripts\dev-windows.ps1"
    exit 1
}

$frontend = Resolve-FrontendBase -Preferred $BaseUrl -ApiBase $api -ProjectRoot $Root
if (-not $frontend) { $frontend = "http://127.0.0.1:3000" }

if (-not $SkipEnvSync) {
    Sync-FrontendApiEnv -ApiBase $api -ProjectRoot $Root
}

Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm install }

$env:E2E_FULL_STACK = "1"
$env:PLAYWRIGHT_BASE_URL = $frontend

if ($GoldenPathOnly) {
    $specList = @("e2e/smoke.spec.ts", "e2e/lab-flow.spec.ts")
} else {
    $specList = @(
        "e2e/smoke.spec.ts",
        "e2e/lab-flow.spec.ts",
        "e2e/invite-flow.spec.ts",
        "e2e/offense-promotion.spec.ts",
        "e2e/maintenance-flow.spec.ts",
        "e2e/intel-crud.spec.ts",
        "e2e/threat-scores.spec.ts"
    )
}

Write-Host "==> Playwright E2E"
Write-Host "    API:  $api"
Write-Host "    UI:   $frontend"
Write-Host "    Specs: $($specList -join ', ')"

npx playwright test @specList --workers=1
exit $LASTEXITCODE
