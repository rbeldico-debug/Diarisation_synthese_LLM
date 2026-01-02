@echo off
chcp 65001 >nul
title Lanceur Océane v2.5

echo ========================================================
echo 🛑 NETTOYAGE DES PROCESSUS FANTÔMES
echo ========================================================
:: Tue tous les processus python.exe (Force et Arbre de processus)
taskkill /F /IM python.exe /T 2>nul
:: Petite pause pour laisser Windows libérer les ports
timeout /t 2 /nobreak >nul
echo.

echo ========================================================
echo 🚀 DÉMARRAGE DU TABLEAU DE BORD (Web Server)
echo ========================================================
:: Lance server.py dans une nouvelle fenêtre minimisée (/min) ou normale
:: On active l'environnement virtuel avant
start "Oceane Dashboard" cmd /k ".venv\Scripts\activate & python server.py"
echo Dashboard lancé sur le port 8002/8003...
timeout /t 3 /nobreak >nul
echo.

echo ========================================================
echo 🌊 DÉMARRAGE DU CERVEAU (Main Engine)
echo ========================================================
:: Lance main.py dans la fenêtre actuelle
call .venv\Scripts\activate
python main.py

:: Si main.py s'arrête, on propose de fermer
echo.
echo [FIN DE SESSION]
pause