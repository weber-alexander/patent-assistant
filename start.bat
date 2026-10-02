@echo off
setlocal
cd /d "%~dp0"
title Patent-Assistent
echo.
echo  Patent-Assistent wird gestartet ...
echo.

rem --- 1. uv (verwaltet Python und alle Pakete) ---
where uv >nul 2>nul
if errorlevel 1 (
    echo  [1/4] uv wird installiert ...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

rem --- 2. Ollama (fuehrt die KI-Modelle lokal aus) ---
where ollama >nul 2>nul
if errorlevel 1 (
    echo  [2/4] Ollama wird installiert ...
    winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
)
set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"

ollama list >nul 2>nul
if errorlevel 1 (
    echo  [3/4] Ollama wird gestartet ...
    start "" /min ollama serve
    timeout /t 5 /nobreak >nul
)

rem --- 3. Pakete installieren (beim ersten Start einige Minuten) ---
echo  [4/4] Pakete werden geprueft ...
uv sync --frozen --no-dev
if errorlevel 1 (
    echo.
    echo  Fehler bei der Installation. Bitte Internetverbindung pruefen.
    pause
    exit /b 1
)

rem --- 4. Browser nach kurzer Wartezeit oeffnen und App starten ---
echo.
echo  Die App oeffnet sich im Browser. Dieses Fenster bitte geoeffnet lassen.
echo  Zum Beenden das Fenster schliessen.
echo.
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:8501"
uv run --frozen streamlit run src/patent_assistant/app.py --server.headless true

pause