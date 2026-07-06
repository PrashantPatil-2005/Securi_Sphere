# Print agent install command and verify host status (run after enrolling a host in the UI).
param(
    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,
    [Parameter(Mandatory = $true)]
    [string]$EnrollToken
)

Write-Host "Run this on your Ubuntu VM:"
Write-Host ""
Write-Host "curl -fsSL ${ServerUrl}/install.sh | sudo bash -s -- --token $EnrollToken --server $ServerUrl"
Write-Host ""
Write-Host "Verify on the dashboard:"
Write-Host "  Hosts page -> status should show online within 60s"
Write-Host "  Events page -> agent heartbeats and log events appear"
Write-Host "  Live security feed -> real-time updates"
Write-Host ""
Write-Host "API check (replace HOST_ID):"
Write-Host "  GET ${ServerUrl}/api/v1/hosts"
