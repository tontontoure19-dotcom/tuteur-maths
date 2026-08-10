@echo off
chcp 65001 >nul
title Codes d'acces - Tuteur Maths
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Environnement introuvable. Lancez d'abord DEMARRER.bat une fois.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" outils\generer_codes.py %*

if exist "codes.txt" start "" notepad "codes.txt"
pause
