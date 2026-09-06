# One-command local dev start for Securi on Windows.
param(
    [switch]$Demo,
    [string]$LanIp = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. "$PSScriptRoot\ensure-docker-env.ps1"
. "$PSScriptRoot\lan-url.ps1"
Ensure-DockerEnv | Out-Null

function Wait-Postgres {
    $max = 30
    for ($i = 0; $i -lt $max; $i++) {
        $ok = docker exec securi-postgres pg_isready -U securi -d securi 2>$null
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Seconds 2
    }
    throw "Postgres did not become ready in time"
}

Write-Host "==> Starting Postgres + Redis"
docker compose -f docker-compose.dev.yml up -d
Wait-Postgres

# Ensure backend .env exists
if (-not (Test-Path "$Root\backend\.env")) {
    if (Test-Path "$Root\.env") {
        Copy-Item "$Root\.env" "$Root\backend\.env"
    } elseif (Test-Path "$Root\.env.example") {
        Copy-Item "$Root\.env.example" "$Root\backend\.env"
        Add-Content "$Root\backend\.env" @"

POSTGRES_PASSWORD=securi_dev
DATABASE_URL=postgresql+asyncpg://securi:securi_dev@localhost:5432/securi
JWT_SECRET=dev-jwt-secret-change-in-production-min-32-chars
REDIS_URL=redis://localhost:6379/0
SQL_ECHO=false
"@
    }
}

$resolvedLan = Get-PreferredLanIPv4 -LanIp $LanIp
Set-SecuriLanUrls -ProjectRoot $Root -LanIp $resolvedLan | Out-Null
Write-Host "SERVER_URL=http://${resolvedLan}:8000 (agents). If DHCP changes: .\scripts\sync-lan-urls.ps1"

. "$PSScriptRoot\ensure-docker-env.ps1"
Ensure-DockerEnv | Out-Null
# Same-machine browser uses loopback; Kali agents use SERVER_URL.
$preferredApi = "http://127.0.0.1:8000"
$apiUrl = Resolve-ApiBase -Preferred $preferredApi -ProjectRoot $Root
Set-Content -Encoding utf8 "$Root\frontend\.env.local" "NEXT_PUBLIC_API_URL=$apiUrl"

Write-Host "==> Backend venv + migrations"
Set-Location "$Root\backend"
if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\pip install -r requirements.txt -q
.\venv\Scripts\alembic upgrade head

Write-Host "==> Starting backend on :8000"
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$Root\backend'; .\venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
) | Out-Null

Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) {
    npm install
}

if ($Demo) {
    Write-Host "==> Demo mode: building production frontend"
    npm run build
    Write-Host "==> Starting frontend on :3000 (npm start)"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$Root\frontend'; npm run start"
    ) | Out-Null
} else {
    Write-Host "==> Starting frontend dev server on :3000 (Turbopack)"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$Root\frontend'; npm run dev"
    ) | Out-Null
}

Write-Host ""
Write-Host "Securi is starting."
Write-Host "  Dashboard (this PC): http://127.0.0.1:3000"
Write-Host "  Dashboard (LAN):     http://${resolvedLan}:3000"
Write-Host "  API docs (this PC):  $apiUrl/docs"
Write-Host "  API (LAN / agents):  http://${resolvedLan}:8000"
Write-Host "  Bind:                0.0.0.0:8000"
Write-Host "  LAN:                 .\scripts\open-firewall.ps1"
Write-Host ""
Write-Host "Verify: .\scripts\verify-local.ps1"
Write-Host "Stop with: .\scripts\dev-stop.ps1"
