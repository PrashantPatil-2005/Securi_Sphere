# One-command local dev start for Securi on Windows.
param(
    [switch]$Demo,
    [string]$LanIp = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

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
docker compose up -d postgres redis
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

# Ensure frontend .env.local
$apiUrl = if ($LanIp) { "http://${LanIp}:8000" } else { "http://localhost:8000" }
Set-Content -Encoding utf8 "$Root\frontend\.env.local" "NEXT_PUBLIC_API_URL=$apiUrl"

Write-Host "==> Backend venv + migrations"
Set-Location "$Root\backend"
if (-not (Test-Path "venv")) {
    python -m venv venv
    .\venv\Scripts\pip install -r requirements.txt
}
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
Write-Host "  Dashboard: http://localhost:3000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Dev login: admin@test.local / testpass123"
if ($LanIp) {
    Write-Host "  LAN:       http://${LanIp}:3000 (open firewall for 3000, 8000)"
}
Write-Host ""
Write-Host "Stop with: .\scripts\dev-stop.ps1"
