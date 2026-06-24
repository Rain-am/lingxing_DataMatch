$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$StartScript = Join-Path $Root "scripts\start-app.ps1"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

$Process = Start-Process `
  -FilePath $PowerShell `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $StartScript) `
  -WorkingDirectory $Root `
  -WindowStyle Hidden `
  -PassThru

Start-Sleep -Seconds 6

$HealthOk = $false
try {
  $HealthOk = ((Invoke-RestMethod "http://127.0.0.1:8000/api/health" -TimeoutSec 5).status -eq "ok")
} catch {
  $HealthOk = $false
}

if ($HealthOk) {
  Write-Host "Started: http://127.0.0.1:8000/"
  Write-Host "Launcher PID: $($Process.Id)"
} else {
  Write-Host "Start command issued, but health check is not ready yet. Check backend-server.log."
  Write-Host "Launcher PID: $($Process.Id)"
}
