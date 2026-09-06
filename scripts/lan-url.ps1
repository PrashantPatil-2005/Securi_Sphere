# Shared LAN URL helpers. Dot-source from other scripts:
#   . "$PSScriptRoot\lan-url.ps1"

function Get-LocalIPv4Addresses {
    $rows = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue
    if (-not $rows) { return @() }
    $rows |
        Where-Object {
            $_.IPAddress -and
            $_.IPAddress -notmatch '^(127\.|169\.254\.)'
        } |
        Select-Object -ExpandProperty IPAddress -Unique
}

function Get-PreferredLanIPv4 {
    param([string]$LanIp = "")

    if ($LanIp) {
        $trimmed = $LanIp.Trim()
        Assert-LanIpOnLocalInterface -LanIp $trimmed
        return $trimmed
    }

    $upIfs = @(Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.ConnectionState -eq "Connected" -and $_.InterfaceAlias -notmatch 'Loopback' } |
        Select-Object -ExpandProperty InterfaceIndex)

    $candidates = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -and
            $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and
            ($upIfs.Count -eq 0 -or $upIfs -contains $_.InterfaceIndex)
        })

    $preferred = @($candidates | Where-Object {
        $_.InterfaceAlias -match 'Wi-?Fi|Wireless|Ethernet|LAN' -and
        $_.PrefixOrigin -eq "Dhcp"
    })
    if ($preferred.Count -eq 0) {
        $preferred = @($candidates | Where-Object { $_.PrefixOrigin -eq "Dhcp" })
    }
    if ($preferred.Count -eq 0) {
        $preferred = $candidates
    }

    $ips = @($preferred | Select-Object -ExpandProperty IPAddress -Unique)
    if ($ips.Count -eq 1) { return $ips[0] }
    if ($ips.Count -eq 0) {
        throw "No usable LAN IPv4 address found. Pass -LanIp <current-wifi-ip> explicitly."
    }

    $listed = ($ips | ForEach-Object { "  $_" }) -join "`n"
    throw @"
Multiple LAN IPv4 addresses are assigned. Pass -LanIp with the address agents should use.

$listed

Do not hardcode a Wi-Fi IP in source; DHCP leases change.
"@
}

function Assert-LanIpOnLocalInterface {
    param([Parameter(Mandatory = $true)][string]$LanIp)

    $ip = $LanIp.Trim()
    if ($ip -match '^https?://') {
        try {
            $ip = ([System.Uri]$ip).Host
        } catch {
            throw "Invalid URL: $LanIp"
        }
    }

    if ($ip -in @("localhost", "127.0.0.1", "::1")) { return }

    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($ip, [ref]$parsed)) { return }

    if ($parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) { return }
    if ($ip -match '^(127\.|169\.254\.)') { return }

    $local = @(Get-LocalIPv4Addresses)
    if ($local -contains $ip) { return }

    $listed = if ($local.Count) { ($local | ForEach-Object { "  $_" }) -join "`n" } else { "  (none)" }
    throw @"
SERVER_URL / -LanIp host '$ip' is not assigned to any local network interface.
This machine currently has:
$listed

Wi-Fi DHCP addresses change. Re-run with -LanIp set to a current address from the list above
(or run .\scripts\sync-lan-urls.ps1). Do not hardcode 192.168.0.x in source or docs.
"@
}

function Assert-ServerUrlOnLocalInterface {
    param([string]$ServerUrl)

    if (-not $ServerUrl) { return }
    Assert-LanIpOnLocalInterface -LanIp $ServerUrl
}

function Set-EnvFileKey {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
    $lines = @()
    $found = $false
    if (Test-Path $Path) {
        $lines = @(Get-Content -Path $Path)
        $lines = @(
            $lines | ForEach-Object {
                if ($_ -match "^$([regex]::Escape($Key))=") {
                    $found = $true
                    "$Key=$Value"
                } else {
                    $_
                }
            }
        )
    }
    if (-not $found) {
        $lines += "$Key=$Value"
    }
    Set-Content -Encoding utf8 -Path $Path -Value $lines
}

function Set-SecuriLanUrls {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$LanIp,
        [string]$ApiPort = "8000",
        [string]$FrontendPort = "3000",
        [switch]$PublishOnAllInterfaces
    )

    Assert-LanIpOnLocalInterface -LanIp $LanIp
    $serverUrl = "http://${LanIp}:${ApiPort}"
    $frontendUrl = "http://${LanIp}:${FrontendPort}"

    $rootEnv = Join-Path $ProjectRoot ".env"
    $backendEnv = Join-Path $ProjectRoot "backend\.env"
    $frontendEnv = Join-Path $ProjectRoot "frontend\.env.local"

    foreach ($envFile in @($rootEnv, $backendEnv)) {
        if (-not (Test-Path $envFile)) { continue }
        Set-EnvFileKey -Path $envFile -Key "SERVER_URL" -Value $serverUrl
        Set-EnvFileKey -Path $envFile -Key "FRONTEND_URL" -Value $frontendUrl
        if ($PublishOnAllInterfaces) {
            Set-EnvFileKey -Path $envFile -Key "BACKEND_HOST_BIND" -Value "0.0.0.0"
            Set-EnvFileKey -Path $envFile -Key "FRONTEND_HOST_BIND" -Value "0.0.0.0"
        }
    }

    if (Test-Path (Split-Path -Parent $frontendEnv)) {
        # Browser on this Windows host can keep loopback; agents use SERVER_URL.
        Set-EnvFileKey -Path $frontendEnv -Key "NEXT_PUBLIC_API_URL" -Value "http://127.0.0.1:${ApiPort}"
    }

    return @{
        LanIp        = $LanIp
        ServerUrl    = $serverUrl
        FrontendUrl  = $frontendUrl
    }
}
