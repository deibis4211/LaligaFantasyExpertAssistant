# Script para iniciar el ecosistema web de LaLiga Fantasy Expert Assistant

Write-Host "======================================================" -ForegroundColor Green
Write-Host "  INICIANDO LALIGA FANTASY EXPERT ASSISTANT WEB" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green

# 1. Arrancar el Backend (FastAPI) en una nueva consola para ver sus logs
Write-Host "[*] Iniciando Servidor Backend (FastAPI) en puerto 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$Host.UI.RawUI.WindowTitle='Fantasy Backend API'; C:/Users/David/AppData/Local/Programs/Python/Python311/python.exe -m uvicorn app:app --port 8000 --reload"

# 2. Arrancar el Frontend (Vite + React) en la consola actual
Write-Host "[*] Iniciando Servidor Frontend (Vite) en puerto 5173..." -ForegroundColor Yellow
Set-Location frontend
npm run dev
