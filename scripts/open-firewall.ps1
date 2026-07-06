# Open Windows Firewall for Securi LAN pilot (run as Administrator).
param(
    [int]$FrontendPort = 3000,
    [int]$ApiPort = 8000
)

$ErrorActionPreference = "Stop"
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Run this script in an elevated PowerShell session."
}

New-NetFirewallRule -DisplayName "Securi Frontend" -Direction Inbound -Protocol TCP -LocalPort $FrontendPort -Action Allow -ErrorAction SilentlyContinue | Out-Null
New-NetFirewallRule -DisplayName "Securi API" -Direction Inbound -Protocol TCP -LocalPort $ApiPort -Action Allow -ErrorAction SilentlyContinue | Out-Null
Write-Host "Firewall rules added for TCP $FrontendPort and $ApiPort"
