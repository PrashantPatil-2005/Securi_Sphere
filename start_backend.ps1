param(
    [int]$Port = 8000
)

$Env:SERVER_URL = "http://10.0.9.93:$Port"
$Env:FRONTEND_URL = "http://localhost:3000"

Write-Host "Starting Securi Backend on port $Port..."
Write-Host "SERVER_URL: $Env:SERVER_URL"
Write-Host "FRONTEND_URL: $Env:FRONTEND_URL"

$ErrorActionPreference = "Stop"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $Port