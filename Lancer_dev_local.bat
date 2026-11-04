@echo off
rem Dynamite | Agile -- lancement en DEVELOPPEMENT, mode local (D-B-091). Jamais pour la production.
rem Ce poste seulement : http://localhost:8080 (admin / admin pre-rempli).
cd /d "%~dp0"
set "PY="
for %%P in ("%USERPROFILE%\anaconda3\python.exe" "%LOCALAPPDATA%\anaconda3\python.exe" "%ProgramData%\anaconda3\python.exe" "%USERPROFILE%\miniconda3\python.exe" "%LOCALAPPDATA%\miniconda3\python.exe") do (
  if not defined PY if exist %%P set "PY=%%~P"
)
if not defined PY (
  for /f "delims=" %%P in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do if not defined PY set "PY=%%P"
)
if not defined PY (
  echo Python introuvable. Ouvrez lancer_dev.py dans Spyder et appuyez sur F5 (MODE = "local").
  pause
  exit /b 1
)
echo Python : %PY%
"%PY%" lancer_dev.py local %*
pause
