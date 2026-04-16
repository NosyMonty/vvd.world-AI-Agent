@echo off
<<<<<<< HEAD
title vvd.world AI Agent
=======
title vvd.world AI Agent Launcher
>>>>>>> 8df96f4 (API added along with TUI and more streamlined folder structure)

echo ==========================================
echo   vvd.world AI Agent - Starting up...
echo ==========================================
echo.

<<<<<<< HEAD
echo [1/4] Checking for existing Ollama processes...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo       Found Ollama running - closing it...
    taskkill /F /IM ollama.exe >NUL 2>&1
    taskkill /F /IM "ollama app.exe" >NUL 2>&1
    timeout /t 2 /nobreak > nul
    echo       Ollama closed!
) else (
    echo       No existing Ollama found.
)
=======
echo [1/4] Closing any existing Ollama processes...
taskkill /F /IM ollama.exe >NUL 2>&1
taskkill /F /IM ollama-lib.exe >NUL 2>&1
taskkill /F /IM "ollama app.exe" >NUL 2>&1
timeout /t 2 /nobreak >NUL
echo       Done!
>>>>>>> 8df96f4 (API added along with TUI and more streamlined folder structure)

echo.
echo [2/4] Starting Ollama with Intel GPU...
cd /d C:\ipex-ollama
<<<<<<< HEAD
start "Ollama GPU Server" start-ollama.bat
timeout /t 5 /nobreak > nul
echo       Ollama GPU server started!

echo.
echo [3/4] Activating Python environment...
cd /d C:\Users\noahm\vvw-agent
call .venv\Scripts\activate.bat
echo       Environment ready!

echo.
echo [4/4] Launching agent...
echo.
echo ==========================================
python agent.py

echo.
echo ==========================================
echo   Agent closed. Press any key to exit.
echo ==========================================
echo
pause
echo Shutting down...
taskkill /F /IM ollama-lib.exe >NUL 2>&1
taskkill /F /IM ollama.exe >NUL 2>&1
taskkill /FI "WINDOWTITLE eq IPEX-LLM Ollama erve" /F >NUL 2>&1
taskkill /FI "WINDOWTITLE eq Ollama GPU Server" /F >NUL 2>&1
//ping -n 2 127.0.0.1 >NUL
taskkill /FI "WINDOWTITLE eq IPEX-LLM Ollama Serve" /F >NUL 2>&1
taskkill /FI "WINDOWTITLE eq Ollama GPU Server" /F >NUL 2>&1
//ping -n 2 127.0.0.1 >NUL
taskkill /FI "WINDOWTITLE eq IPEX-LLM Ollama Serve" /F >NUL 2>&1
taskkill /FI "WINDOWTITLE eq Ollama GPU Server" /F >NUL 2>&1
exit
=======
start "IPEX Ollama GPU" cmd /c "start-ollama.bat"
timeout /t 6 /nobreak >NUL
echo       Ollama GPU server started!

echo.
echo [3/4] Starting FastAPI server...
cd /d C:\Users\noahm\vvw-agent
call .venv\Scripts\activate.bat
start "vvw-agent API" cmd /k "cd /d C:\Users\noahm\vvw-agent && .venv\Scripts\activate.bat && uvicorn api.main:app"
timeout /t 4 /nobreak >NUL
echo       API server started at http://localhost:8000

echo.
echo [4/4] Starting Terminal UI...
start "vvw-agent TUI" cmd /k "cd /d C:\Users\noahm\vvw-agent && .venv\Scripts\activate.bat && python tui/app.py & echo. & echo TUI closed. Press any key to exit.."
echo TUI launched!

echo.
echo ==========================================
echo   All services running!
echo.
echo   API Docs : http://localhost:8000/docs
echo   Health   : http://localhost:8000/health
echo.
echo   Close this window when done.
echo   The API and TUI windows will stay open.
echo ==========================================
echo.

pause

echo.
echo Shutting everything down...
taskkill /F /IM ollama-lib.exe >NUL 2>&1
taskkill /F /IM ollama.exe >NUL 2>&1
taskkill /FI "WINDOWTITLE eq vvw-agent API" /F >NUL 2>&1
taskkill /FI "WINDOWTITLE eq vvw-agent TUI" /F >NUL 2>&1
taskkill /FI "WINDOWTITLE eq IPEX Ollama GPU" /F >NUL 2>&1
echo Done! All services stopped.
timeout /t 2 /nobreak >NUL
>>>>>>> 8df96f4 (API added along with TUI and more streamlined folder structure)
