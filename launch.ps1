param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$fleetRoot = $PSScriptRoot
$fleetPort = if ($env:FLEET_PORT) { [int]$env:FLEET_PORT } else { 4173 }
$fleetUrl = "http://127.0.0.1:$fleetPort"
$fleetHealthy = $false
try {
    $fleetHealth = Invoke-RestMethod "$fleetUrl/api/health" -TimeoutSec 2
    if ($fleetHealth.app -ne 'galaxies-fleet-planner' -or $fleetHealth.root -ne $fleetRoot) { throw 'Another application is using the planner port.' }
    $fleetHealthy = $true
} catch {
    if ($_.Exception.Message -eq 'Another application is using the planner port.') { throw }
}
if (-not $fleetHealthy) {
    $fleetNode = Get-Command node -ErrorAction SilentlyContinue
    if (-not $fleetNode) { throw 'Node.js 20 or newer is required. Install Node.js from nodejs.org, then reopen this launcher.' }
    $fleetMajor = [int]((& $fleetNode.Source --version).TrimStart('v').Split('.')[0])
    if ($fleetMajor -lt 20) { throw 'Please update Node.js to version 20 or newer.' }
    $fleetData = Join-Path $fleetRoot 'local-data'
    New-Item -ItemType Directory -Path $fleetData -Force | Out-Null
    $fleetServer = Join-Path $fleetRoot 'server.mjs'
    $fleetProcess = Start-Process -FilePath $fleetNode.Source -ArgumentList ('"' + $fleetServer + '"') -WorkingDirectory $fleetRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $fleetData 'server.log') -RedirectStandardError (Join-Path $fleetData 'server-error.log') -PassThru
    $fleetProcess.Id | Set-Content (Join-Path $fleetData 'server.pid')
    for ($fleetAttempt = 0; $fleetAttempt -lt 30; $fleetAttempt++) {
        Start-Sleep -Milliseconds 200
        try {
            $fleetHealth = Invoke-RestMethod "$fleetUrl/api/health" -TimeoutSec 1
            if ($fleetHealth.app -eq 'galaxies-fleet-planner' -and $fleetHealth.root -eq $fleetRoot) { $fleetHealthy = $true; break }
        } catch { }
    }
    if (-not $fleetHealthy) { throw 'Planner could not start. Check local-data/server-error.log or choose another FLEET_PORT.' }
}
if (-not $NoBrowser) { Start-Process $fleetUrl }
Write-Output "Fleet planner ready: $fleetUrl"
