@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python ausente. Consulte chaoslab\GUIA.txt.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)" >nul 2>&1
if not errorlevel 1 (
  start "" "http://127.0.0.1:8501"
  exit /b 0
)
start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "$deadline = (Get-Date).AddSeconds(60); while ((Get-Date) -lt $deadline) { try { $health = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8501/_stcore/health' -TimeoutSec 1; if ($health.StatusCode -eq 200 -and $health.Content.Trim() -eq 'ok') { Start-Process 'http://127.0.0.1:8501'; exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
".venv\Scripts\python.exe" -m streamlit run chaoslab/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
pause
