# Verify local Securi dev stack (Postgres, Redis, API, optional frontend).
param(
    [string]$ApiBase = "",
    [string]$FrontendBase = "",
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. "$PSScriptRoot\ensure-docker-env.ps1"
Ensure-DockerEnv | Out-Null

function Read-EnvValue {
    param([string]$File, [string]$Key)
    if (-not (Test-Path $File)) { return $null }
    $line = Select-String -Path $File -Pattern "^$Key=(.*)$" | Select-Object -First 1
    if (-not $line) { return $null }
    return $line.Matches[0].Groups[1].Value.Trim()
}

if (-not $ApiBase) {
    $ApiBase = Read-EnvValue "$Root\backend\.env" "SERVER_URL"
    if (-not $ApiBase) { $ApiBase = "http://localhost:8000" }
}
$configuredApi = $ApiBase
$ApiBase = Resolve-ApiBase -Preferred $configuredApi -ProjectRoot $Root
if (-not $FrontendBase) {
    $FrontendBase = Read-EnvValue "$Root\backend\.env" "FRONTEND_URL"
    if (-not $FrontendBase) { $FrontendBase = "http://localhost:3000" }
}
$configuredFrontend = $FrontendBase
$FrontendBase = Resolve-FrontendBase -Preferred $configuredFrontend -ApiBase $ApiBase -ProjectRoot $Root

$failures = @()

$apiLabel = $ApiBase
if ($configuredApi -and $configuredApi -ne $ApiBase) {
    $apiLabel = "$ApiBase (configured: $configuredApi)"
}
$frontendLabel = $FrontendBase
if ($configuredFrontend -and $configuredFrontend -ne $FrontendBase) {
    $frontendLabel = "$FrontendBase (configured: $configuredFrontend)"
}
Write-Host "==> Securi local verification"
Write-Host "    API:       $apiLabel"
Write-Host "    Frontend:  $frontendLabel"
Write-Host ""

Write-Host "==> Docker services"
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker daemon not running" }
    foreach ($svc in @("securi-postgres", "securi-redis")) {
        $running = docker inspect -f "{{.State.Running}}" $svc 2>$null
        if ($running -eq "true") {
            Write-Host "  OK  $svc"
        } else {
            Write-Host "  FAIL $svc (not running)"
            $failures += $svc
        }
    }
} catch {
    Write-Host "  WARN Docker unavailable - $($_.Exception.Message)"
    Write-Host "       Start Docker Desktop, then: docker compose up -d postgres redis"
}

Write-Host ""
Write-Host "==> API health"
try {
    $live = Invoke-RestMethod -Uri "$ApiBase/health/live" -TimeoutSec 5
    if ($live.status -eq "alive") { Write-Host "  OK  /health/live" } else { throw "unexpected status" }
} catch {
    Write-Host "  FAIL /health/live - $($_.Exception.Message)"
    $failures += "api-live"
}

try {
    $ready = Invoke-RestMethod -Uri "$ApiBase/health/ready" -TimeoutSec 10
    Write-Host "  OK  /health/ready ($($ready.status))"
    foreach ($entry in $ready.checks.PSObject.Properties) {
        Write-Host "       $($entry.Name): $($entry.Value)"
    }
} catch {
    Write-Host "  FAIL /health/ready - $($_.Exception.Message)"
    $failures += "api-ready"
}

try {
    $settings = Invoke-RestMethod -Uri "$ApiBase/api/v1/settings/public" -TimeoutSec 5
    Write-Host "  OK  /api/v1/settings/public (env=$($settings.environment), simulation=$($settings.simulation_enabled))"
} catch {
    Write-Host "  FAIL /api/v1/settings/public - $($_.Exception.Message)"
    $failures += "api-settings"
}

if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "==> Frontend"
    if ($FrontendBase -and $FrontendBase -ne $configuredFrontend) {
        Write-Host "  OK  $FrontendBase"
    } elseif ($FrontendBase) {
        try {
            $res = Invoke-WebRequest -Uri $FrontendBase -UseBasicParsing -TimeoutSec 8
            if ($res.StatusCode -ge 200 -and $res.StatusCode -lt 400) {
                Write-Host "  OK  $FrontendBase ($($res.StatusCode))"
            } else {
                throw "HTTP $($res.StatusCode)"
            }
        } catch {
            Write-Host "  WARN $FrontendBase - $($_.Exception.Message) (start with .\scripts\dev-windows.ps1)"
        }
    } else {
        Write-Host "  WARN no reachable frontend (start with .\scripts\dev-windows.ps1)"
    }
}

Write-Host ""
if ($failures.Count -eq 0) {
    Write-Host "All critical checks passed."
    Write-Host "  Dev login: admin@test.local / testpass123"
    $demoMode = Read-EnvValue "$Root\backend\.env" "DEMO_MODE"
    if ($demoMode -eq "true") {
        Write-Host "  Demo login: demo@securi.local / Demo1234!"
    }
    exit 0
}

Write-Host "Failed checks: $($failures -join ', ')"
Write-Host "Start stack: .\scripts\dev-windows.ps1"
exit 1
