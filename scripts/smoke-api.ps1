# Smoke-test key API endpoints (requires backend running on :8000).
$ErrorActionPreference = "Stop"
$Base = "http://localhost:8000"
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

$login = Invoke-WebRequest -Uri "$Base/api/v1/auth/login" -Method POST `
    -Body '{"email":"admin@test.local","password":"testpass123"}' `
    -ContentType "application/json" -WebSession $session -UseBasicParsing
if ($login.StatusCode -ne 200) { throw "Login failed" }

$endpoints = @(
    "/api/v1/auth/me",
    "/api/v1/hosts?page_size=10",
    "/api/v1/events?page_size=10",
    "/api/v1/alerts?page_size=10",
    "/api/v1/offenses?page_size=10",
    "/api/v1/incidents",
    "/api/v1/audit",
    "/api/v1/siem/executive",
    "/api/v1/siem/events-trend",
    "/api/v1/siem/severity-distribution",
    "/api/v1/siem/failed-logins",
    "/api/v1/siem/top-risky-hosts",
    "/api/v1/siem/host-health",
    "/api/v1/mitre/matrix",
    "/api/v1/timeline",
    "/api/v1/network/topology",
    "/api/v1/search/siem?q=severity:high",
    "/api/v1/alert-rules",
    "/api/v1/correlation-rules",
    "/api/v1/reports",
    "/api/v1/system/health",
    "/api/v1/notifications",
    "/api/v1/simulation/scenarios"
)

$failed = @()
foreach ($ep in $endpoints) {
    try {
        $r = Invoke-WebRequest -Uri "$Base$ep" -WebSession $session -UseBasicParsing -TimeoutSec 30
        Write-Host "OK $($r.StatusCode) $ep"
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host "FAIL $code $ep"
        $failed += $ep
    }
}

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "Failed endpoints: $($failed -join ', ')"
    exit 1
}
Write-Host ""
Write-Host "All smoke tests passed."
