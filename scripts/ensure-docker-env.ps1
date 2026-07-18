# Ensures repo-root .env exists for docker compose (Postgres password).
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

function Get-DatabasePasswordFromUrl {
    param([string]$Url)
    if ($Url -match 'postgresql\+asyncpg://[^:]+:([^@]+)@') {
        return $Matches[1]
    }
    return $null
}

function Read-EnvKey {
    param([string]$File, [string]$Key)
    if (-not (Test-Path $File)) { return $null }
    $line = Select-String -Path $File -Pattern "^$Key=(.*)$" | Select-Object -First 1
    if (-not $line) { return $null }
    return $line.Matches[0].Groups[1].Value.Trim()
}

function Ensure-DockerEnv {
    param([string]$ProjectRoot = $Root)

    $rootEnv = Join-Path $ProjectRoot ".env"
    $backendEnv = Join-Path $ProjectRoot "backend\.env"

    $pgUser = "securi"
    $pgDb = "securi"
    $pgPass = $null

    if (Test-Path $rootEnv) {
        $pgPass = Read-EnvKey $rootEnv "POSTGRES_PASSWORD"
        $pgUser = Read-EnvKey $rootEnv "POSTGRES_USER"
        if (-not $pgUser) { $pgUser = "securi" }
        $pgDb = Read-EnvKey $rootEnv "POSTGRES_DB"
        if (-not $pgDb) { $pgDb = "securi" }
    }

    if (-not $pgPass -and (Test-Path $backendEnv)) {
        $pgPass = Read-EnvKey $backendEnv "POSTGRES_PASSWORD"
        if (-not $pgPass) {
            $dbUrl = Read-EnvKey $backendEnv "DATABASE_URL"
            $pgPass = Get-DatabasePasswordFromUrl $dbUrl
        }
    }

    if (-not $pgPass) {
        Write-Warning "No POSTGRES_PASSWORD found in .env files. Using development fallback. DO NOT use in production."
        $pgPass = "securi_dev"
    }

    $lines = @()
    if (Test-Path $rootEnv) {
        $lines = Get-Content $rootEnv | Where-Object { $_ -notmatch '^(POSTGRES_USER|POSTGRES_DB|POSTGRES_PASSWORD)=' }
    }
    $header = @(
        "POSTGRES_USER=$pgUser",
        "POSTGRES_DB=$pgDb",
        "POSTGRES_PASSWORD=$pgPass"
    )
    ($header + $lines) | Set-Content -Encoding utf8 $rootEnv

    return @{
        Password = $pgPass
        User     = $pgUser
        Database = $pgDb
        Path     = $rootEnv
    }
}

function Test-ApiReachable {
    param([string]$Base)
    if (-not $Base) { return $false }
    try {
        $null = Invoke-RestMethod -Uri "$Base/health/live" -TimeoutSec 4
        return $true
    } catch {
        return $false
    }
}

function Resolve-FrontendBase {
    param(
        [string]$Preferred = "",
        [string]$ApiBase = "",
        [string]$ProjectRoot = $Root
    )
    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($Preferred) { $candidates.Add($Preferred) }
    if ($ApiBase) { $candidates.Add(($ApiBase -replace ':8000', ':3000')) }
    if (Test-Path (Join-Path $ProjectRoot "backend\.env")) {
        $fromEnv = Read-EnvKey (Join-Path $ProjectRoot "backend\.env") "FRONTEND_URL"
        if ($fromEnv) { $candidates.Add($fromEnv) }
    }
    $candidates.Add("http://127.0.0.1:3000")
    $candidates.Add("http://localhost:3000")

    $seen = @{}
    foreach ($base in $candidates) {
        if (-not $base -or $seen.ContainsKey($base)) { continue }
        $seen[$base] = $true
        try {
            $res = Invoke-WebRequest -Uri $base -UseBasicParsing -TimeoutSec 5
            if ($res.StatusCode -ge 200 -and $res.StatusCode -lt 400) { return $base }
        } catch {}
    }
    return $Preferred
}

function Resolve-ApiBase {
    param(
        [string]$Preferred = "",
        [string]$ProjectRoot = $Root
    )
    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($Preferred) { $candidates.Add($Preferred) }
    if (Test-Path (Join-Path $ProjectRoot "backend\.env")) {
        $fromEnv = Read-EnvKey (Join-Path $ProjectRoot "backend\.env") "SERVER_URL"
        if ($fromEnv) { $candidates.Add($fromEnv) }
    }
    $candidates.Add("http://127.0.0.1:8000")
    $candidates.Add("http://localhost:8000")

    $seen = @{}
    foreach ($base in $candidates) {
        if (-not $base -or $seen.ContainsKey($base)) { continue }
        $seen[$base] = $true
        if (Test-ApiReachable $base) { return $base }
    }
    return $Preferred
}

function Sync-FrontendApiEnv {
    param(
        [string]$ApiBase,
        [string]$ProjectRoot = $Root
    )
    if (-not $ApiBase) { return }
    $envFile = Join-Path $ProjectRoot "frontend\.env.local"
    Set-Content -Encoding utf8 $envFile "NEXT_PUBLIC_API_URL=$ApiBase"
}

if ($MyInvocation.InvocationName -ne '.') {
    $result = Ensure-DockerEnv
    Write-Host "Docker env ready: $($result.Path) (user=$($result.User), db=$($result.Database))"
}
