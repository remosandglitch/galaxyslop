$ErrorActionPreference = 'Stop'
$fleetPidFile = Join-Path $PSScriptRoot 'local-data/server.pid'
if (-not (Test-Path -LiteralPath $fleetPidFile)) { Write-Output 'No launcher-owned server is recorded.'; exit 0 }
$fleetPid = [int](Get-Content -LiteralPath $fleetPidFile)
$fleetProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$fleetPid"
$fleetExpected = Join-Path $PSScriptRoot 'server.mjs'
if ($fleetProcess -and $fleetProcess.Name -eq 'node.exe' -and $fleetProcess.CommandLine.Contains($fleetExpected)) {
    Stop-Process -Id $fleetPid
    Write-Output 'Fleet planner stopped. Your progress is saved.'
} elseif ($fleetProcess) { throw 'The saved process ID belongs to another process; it has not been stopped.' }
