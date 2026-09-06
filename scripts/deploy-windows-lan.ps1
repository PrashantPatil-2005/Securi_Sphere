# LAN pilot deployment on Windows (Docker Desktop).
# Usage:
#   .\scripts\deploy-windows-lan.ps1
#   .\scripts\deploy-windows-lan.ps1 -LanIp <current-dhcp-ipv4>
param(
    [string]$LanIp = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. "$PSScriptRoot\lan-url.ps1"

$LanIp = Get-PreferredLanIPv4 -LanIp $LanIp
Assert-LanIpOnLocalInterface -LanIp $LanIp

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    $pgPass = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    Set-EnvFileKey -Path ".env" -Key "POSTGRES_USER" -Value "securi"
    Set-EnvFileKey -Path ".env" -Key "POSTGRES_DB" -Value "securi"
    Set-EnvFileKey -Path ".env" -Key "POSTGRES_PASSWORD" -Value $pgPass
    Set-EnvFileKey -Path ".env" -Key "DATABASE_URL" -Value "postgresql+asyncpg://securi:${pgPass}@postgres:5432/securi"
    Set-EnvFileKey -Path ".env" -Key "JWT_SECRET" -Value $jwt
    Set-EnvFileKey -Path ".env" -Key "REDIS_URL" -Value "redis://redis:6379/0"
    Set-EnvFileKey -Path ".env" -Key "JOB_QUEUE_BACKEND" -Value "redis"
    Set-EnvFileKey -Path ".env" -Key "JOB_QUEUE_RUN_WORKERS" -Value "false"
    Set-EnvFileKey -Path ".env" -Key "WS_PUBSUB_BACKEND" -Value "redis"
    Set-EnvFileKey -Path ".env" -Key "ENVIRONMENT" -Value "production"
    Set-EnvFileKey -Path ".env" -Key "DEBUG" -Value "false"
    Set-EnvFileKey -Path ".env" -Key "SQL_ECHO" -Value "false"
    Set-EnvFileKey -Path ".env" -Key "ALLOW_REGISTRATION" -Value "true"
    Set-EnvFileKey -Path ".env" -Key "ENABLE_SIMULATION" -Value "true"
    Set-EnvFileKey -Path ".env" -Key "EXCLUDE_SIMULATED_FROM_DASHBOARD" -Value "true"
    Set-EnvFileKey -Path ".env" -Key "EVENT_PARTITIONING_ENABLED" -Value "false"
    Set-EnvFileKey -Path ".env" -Key "SKIP_SERVER_URL_INTERFACE_CHECK" -Value "true"
}

$urls = Set-SecuriLanUrls -ProjectRoot $Root -LanIp $LanIp -PublishOnAllInterfaces
Copy-Item ".env" "backend\.env" -Force
Set-EnvFileKey -Path "backend\.env" -Key "SKIP_SERVER_URL_INTERFACE_CHECK" -Value "true"

Write-Host "==> Building and starting production stack (API published on 0.0.0.0:8000)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

Write-Host ""
Write-Host "Pilot deployed on LAN:"
Write-Host "  Dashboard: $($urls.FrontendUrl)"
Write-Host "  API:       $($urls.ServerUrl)/docs"
Write-Host "  Installer uses SERVER_URL=$($urls.ServerUrl)"
Write-Host ""
Write-Host "1. Register admin at /register (first user becomes admin)"
Write-Host "   Or set DEMO_MODE=true in .env, restart stack, then use the demo admin from docs"
Write-Host "   Or run .\scripts\demo-setup.ps1 after stack is up"
Write-Host "2. Run .\scripts\pilot-harden.ps1 after first login"
Write-Host "3. Open Windows Firewall: .\scripts\open-firewall.ps1"
Write-Host "4. Install agent: copy the Hosts enroll command (uses SERVER_URL above)"
Write-Host "If Wi-Fi IP changes, run .\scripts\sync-lan-urls.ps1 and restart."
