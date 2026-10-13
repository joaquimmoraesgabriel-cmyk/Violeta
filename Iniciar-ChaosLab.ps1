$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Ambiente Python ausente. Siga a instalação em chaoslab\GUIA.txt.'
}
Set-Location -LiteralPath $projectRoot
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = 'false'
& $pythonExe -m streamlit run chaoslab/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
