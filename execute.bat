@echo off
title OCEANE V2.5 - Orchestrateur
echo 🚀 Démarrage de l'infrastructure d'Océane...

:: 1. Démarrage de Docker
echo [1/3] Vérification des conteneurs Docker...
docker compose up -d

:: 2. Démarrage d'Obsidian (Chemin direct)
echo [2/3] Ouverture d'Obsidian...
start "" "C:\Users\G-i7\AppData\Local\Programs\Obsidian\Obsidian.exe" obsidian://open?vault=Diarisation_Synthese_LLM

:: 3. Lancement d'Océane
echo [3/3] Lancement de l'esprit d'Océane...
:: On lance le script Python et le bat se ferme après
.venv\Scripts\python.exe main.py

exit