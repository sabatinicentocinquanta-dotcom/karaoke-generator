@echo off
if not exist venv (
    echo [ERRORE] Ambiente virtuale non trovato. Esegui prima setup.bat
    pause & exit /b 1
)
call venv\Scripts\activate.bat
python main.py
