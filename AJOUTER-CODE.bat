@echo off
chcp 65001 >nul
title Ajouter un code d'acces - Repetiteur Maths
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Environnement introuvable. Lancez d'abord DEMARRER.bat une fois.
  echo.
  pause
  exit /b 1
)

echo.
echo   ================================================
echo    Fabriquer un code pour un nouveau testeur
echo   ================================================
echo.
echo   Vos codes deja distribues ne seront pas touches.
echo.

set "niveau="
set /p "niveau=  Niveau (tapez BEPC ou BAC) : "
if /i not "%niveau%"=="BEPC" if /i not "%niveau%"=="BAC" (
  echo.
  echo   Il faut ecrire BEPC ou BAC. Relancez le raccourci.
  echo.
  pause
  exit /b 1
)

set "personne="
set /p "personne=  Prenom de la personne     : "

echo.
".venv\Scripts\python.exe" outils\generer_codes.py "%niveau%=%personne%"

echo   Le nouveau code est a la fin du fichier qui va s'ouvrir.
echo.
echo   ATTENTION : dans Render, AJOUTEZ-le a la fin de CODE_ACCES,
echo   sans effacer les codes deja presents.
echo.

if exist "codes.txt" start "" notepad "codes.txt"
pause
