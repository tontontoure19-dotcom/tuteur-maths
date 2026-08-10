@echo off
chcp 65001 >nul
title Tuteur Maths - BEPC
cd /d "%~dp0backend"

echo.
echo   ================================================
echo      TUTEUR MATHS - BEPC
echo   ================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo   [!] Installation manquante.
    echo       Ouvrez le README et suivez l'etape 2.
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo   [!] Fichier .env introuvable : la cle API manque.
    echo       Ouvrez le README et suivez l'etape 1.
    echo.
    pause
    exit /b 1
)

echo   Demarrage en cours...
echo.
echo   Quand vous verrez "Application startup complete",
echo   ouvrez ces adresses dans Chrome :
echo.
echo      Pour l'eleve  :  http://localhost:8100
echo      Pour le parent:  http://localhost:8100/parent.html
echo.
echo   Pour arreter : fermez cette fenetre.
echo   ------------------------------------------------
echo.

start "" http://localhost:8100
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8100

echo.
echo   Le serveur s'est arrete.
pause
