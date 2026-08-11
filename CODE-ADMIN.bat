@echo off
chcp 65001 >nul
title Code responsable - Tuteur Maths
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Environnement introuvable. Lancez d'abord DEMARRER.bat une fois.
  echo.
  pause
  exit /b 1
)

echo.
echo   Fabrication de votre code de responsable...
echo   Vos codes deja distribues ne sont pas touches.
echo.

".venv\Scripts\python.exe" outils\generer_codes.py ADMIN

echo   Le code est a la fin du fichier qui va s'ouvrir.
echo   Collez-le dans Render sous CODE_ADMIN (pas dans CODE_ACCES).
echo.

if exist "codes.txt" start "" notepad "codes.txt"
pause
