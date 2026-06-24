$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = "C:\Users\Wang\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Node = "C:\Users\Wang\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogPath = Join-Path $Root "backend-server.log"

Set-Location $FrontendDir
& $Node "node_modules\vite\bin\vite.js" build

$Existing = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($PidValue in $Existing) {
  if ($PidValue) {
    Stop-Process -Id $PidValue -Force -ErrorAction SilentlyContinue
  }
}

Set-Location $BackendDir
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 *> $LogPath
