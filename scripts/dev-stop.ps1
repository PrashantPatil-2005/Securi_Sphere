# Stop local Securi dev processes (uvicorn + Next.js) on Windows.
$ErrorActionPreference = "SilentlyContinue"

Get-Process -Name "node", "python" | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmd -match "Securi\\frontend|Securi\\backend|uvicorn app\.main|next dev") {
            Stop-Process -Id $_.Id -Force
            Write-Host "Stopped PID $($_.Id)"
        }
    } catch {}
}

Write-Host "Dev processes stopped. Docker containers (postgres/redis) are left running."
Write-Host "To stop Docker: docker compose down"
