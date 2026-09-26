@echo off
rem Iki klik -> movzu yaz -> hazir YouTube videosu (Episodes\<slug>\).
rem Fon musiqisi her epizod ucun AI ile yaradilir (Stable Audio Open, lokal GPU, pulsuz, istinadsiz).
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

rem Musiqi: pipeline music_gen merhelesinde Episodes\<slug>\music.wav yaradir
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
