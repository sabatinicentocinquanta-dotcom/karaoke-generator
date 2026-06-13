@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo  Karaoke Generator — Setup
echo ============================================================
echo.

REM ── Verifica Python ──────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato. Installa Python 3.10+ da https://python.org
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% trovato

REM ── Crea venv ────────────────────────────────────────────────
if exist venv (
    echo [OK] Ambiente virtuale gia' esistente
) else (
    echo Creazione ambiente virtuale...
    python -m venv venv
    echo [OK] venv creato
)

REM ── Attiva venv ──────────────────────────────────────────────
call venv\Scripts\activate.bat

REM ── Aggiorna pip ─────────────────────────────────────────────
echo Aggiornamento pip...
python -m pip install --upgrade pip --quiet

REM ── Installa PyTorch con CUDA ─────────────────────────────────
echo.
echo Installazione PyTorch con supporto CUDA 12.1...
echo (se hai una versione CUDA diversa modifica l'URL nel file setup.bat)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
if errorlevel 1 (
    echo [AVVISO] Installazione PyTorch CUDA fallita, installo versione CPU...
    pip install torch --quiet
)

REM ── Verifica CUDA ────────────────────────────────────────────
echo.
python -c "import torch; print('[OK] PyTorch', torch.__version__, '— CUDA disponibile:', torch.cuda.is_available())"

REM ── Installa altri pacchetti ──────────────────────────────────
echo.
echo Installazione dipendenze (stable-ts, moviepy, Pillow)...
pip install -r requirements.txt --quiet
echo [OK] Dipendenze installate

REM ── Verifica FFmpeg ───────────────────────────────────────────
echo.
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVVISO] FFmpeg non trovato nel PATH.
    echo          Installalo con:  winget install ffmpeg
    echo          oppure scaricalo da https://ffmpeg.org e aggiungilo al PATH.
) else (
    echo [OK] FFmpeg trovato
)

echo.
echo ============================================================
echo  Setup completato! Avvia l'app con:  run.bat
echo ============================================================
pause
