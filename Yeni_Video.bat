@echo off
rem Iki klik -> movzu yaz -> hazir YouTube videosu (Episodes\<slug>\).
rem Music\ qovlugundaki .mp3-ler fon musiqisi kimi avtomatik istifade olunur (credits.json -> istinad).
setlocal
cd /d "%~dp0"
set "PY=%~dp0Projects\.venv\Scripts\python.exe"

echo ============================================
echo   ELI5 Business - yeni video
echo ============================================
echo Movzunu ingilisce yaz (mes. What Is Cash Flow?)
echo Yarimciq qalmis videonu davam etdirmek ucun: resume
echo.
set /p "TOPIC=Movzu: "
if not defined TOPIC goto :eof
set "TOPIC=%TOPIC:"=%"

if /i "%TOPIC%"=="resume" goto :resume

rem Musiqi: pipeline Music\*.mp3-den her epizoda bir trek secir (novbe ile)
call :run "%TOPIC%"

goto :done

:resume
dir /b /ad Episodes
set /p "SLUG=Slug: "
if not defined SLUG goto :done
call :run --resume "%SLUG%"

:done
echo.
pause
goto :eof

:run
"%PY%" run.py %*
exit /b %errorlevel%
