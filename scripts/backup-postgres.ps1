# Daily PostgreSQL backup for Docker Compose on Windows.
param(
    [string]$Container = $env:BACKUP_PG_CONTAINER ?? "securi-postgres",
    [string]$DbUser = $env:POSTGRES_USER ?? "securi",
    [string]$DbName = $env:POSTGRES_DB ?? "securi",
    [string]$BackupDir = $env:BACKUP_DIRECTORY ?? "data/backups",
    [int]$RetentionDays = $(if ($env:BACKUP_RETENTION_DAYS) { [int]$env:BACKUP_RETENTION_DAYS } else { 30 })
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"'))
        }
    }
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$archive = Join-Path $BackupDir "securi_pg_$stamp.sql.gz"

Write-Host "Backing up $DbName from $Container -> $archive"
docker exec $Container pg_dump -U $DbUser --no-owner --no-acl $DbName | gzip > $archive

$bytes = (Get-Item $archive).Length
$hash = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
$manifest = @{
    filename = Split-Path $archive -Leaf
    path = $archive
    size_bytes = $bytes
    sha256 = $hash
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    trigger = "cron"
    duration_seconds = 0
    database = $DbName
    status = "completed"
} | ConvertTo-Json -Depth 4

$manifestPath = $archive -replace '\.sql\.gz$', '.manifest.json'
Set-Content -Path $manifestPath -Value $manifest -Encoding utf8

$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem $BackupDir -Filter "securi_pg_*.sql.gz" | Where-Object { $_.LastWriteTime -lt $cutoff } | Remove-Item -Force
Get-ChildItem $BackupDir -Filter "securi_pg_*.manifest.json" | Where-Object { $_.LastWriteTime -lt $cutoff } | Remove-Item -Force

Write-Host "Backup complete ($bytes bytes)"
