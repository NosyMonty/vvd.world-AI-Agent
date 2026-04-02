@echo off
title vvd.world AI Agent

echo ==========================================
echo   vvd.world AI Agent - Starting up...
echo ==========================================
echo.

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

echo.
echo [2/4] Starting Ollama with Intel GPU...
cd /d C:\ipex-ollama
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