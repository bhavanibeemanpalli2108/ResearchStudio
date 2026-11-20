param([switch]$Built, [int]$Port = 8000, [int]$FrontendPort = 5173)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $pythonExe = Join-Path $repoRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create .venv and install .[platform] first. See docs/RESEARCH_PLATFORM.md.' }
    if ($Built) { & $pythonExe -m src.research_platform.dev --no-frontend --port $Port }
    else { & $pythonExe -m src.research_platform.dev --port $Port --frontend-port $FrontendPort }
    exit $LASTEXITCODE
} finally { Pop-Location }
