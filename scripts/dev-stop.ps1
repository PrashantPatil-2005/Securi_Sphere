# Stop local Securi dev processes (uvicorn + Next.js) on Windows.
$ErrorActionPreference = "SilentlyContinue"

$devDir = Split-Path -Parent $PSScriptRoot

Get-Process -Name "node", "python" | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmd -and $cmd -match [regex]::Escape($devDir)) {
            Stop-Process -Id $_.Id -Force
            Write-Host "Stopped PID $($_.Id)"
        }
    } catch {}
}

Write-Host "Dev processes stopped. Docker containers (postgres/redis) are left running."
Write-Host "To stop Docker: docker compose down"
