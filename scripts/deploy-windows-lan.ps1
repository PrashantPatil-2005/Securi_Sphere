# LAN pilot deployment on Windows (Docker Desktop).
# Usage: .\scripts\deploy-windows-lan.ps1 -LanIp 192.168.0.105
param(
    [Parameter(Mandatory = $true)]
    [string]$LanIp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
$pgPass = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })

$envContent = @"
POSTGRES_USER=securi
POSTGRES_DB=securi
POSTGRES_PASSWORD=$pgPass
DATABASE_URL=postgresql+asyncpg://securi:${pgPass}@postgres:5432/securi
JWT_SECRET=$jwt
SERVER_URL=http://${LanIp}:8000
FRONTEND_URL=http://${LanIp}:3000
REDIS_URL=redis://redis:6379/0
JOB_QUEUE_BACKEND=redis
JOB_QUEUE_RUN_WORKERS=false
WS_PUBSUB_BACKEND=redis
ENVIRONMENT=production
DEBUG=false
SQL_ECHO=false
ALLOW_REGISTRATION=true
ENABLE_SIMULATION=true
EXCLUDE_SIMULATED_FROM_DASHBOARD=true
EVENT_PARTITIONING_ENABLED=false
"@

Set-Content -Encoding utf8 ".env" $envContent
Copy-Item ".env" "backend\.env" -Force

Write-Host "==> Building and starting production stack"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

Write-Host ""
Write-Host "Pilot deployed on LAN:"
Write-Host "  Dashboard: http://${LanIp}:3000"
Write-Host "  API:       http://${LanIp}:8000/docs"
Write-Host ""
Write-Host "1. Register admin at /register (first user becomes admin)"
Write-Host "   Or set DEMO_MODE=true in .env, restart stack, login demo@securi.local / Demo1234!"
Write-Host "   Or run .\scripts\demo-setup.ps1 after stack is up"
Write-Host "2. Run .\scripts\pilot-harden.ps1 after first login"
Write-Host "3. Open Windows Firewall for TCP 3000 and 8000"
Write-Host "4. Install agent: see docs/AGENT_INSTALL.md"
