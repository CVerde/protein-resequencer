#!/bin/bash
# Protein Resequencer - Update & Start

cd /home/pi/protein-resequencer

# Arrêter les instances en cours
pkill -f "python3 app.py" 2>/dev/null
pkill -f "chromium.*localhost:5000" 2>/dev/null
pkill -f "wvkbd" 2>/dev/null
pkill -f "onboard" 2>/dev/null
pkill -f "squeekboard" 2>/dev/null

sleep 1

# Mise à jour depuis GitHub
echo "🔄 Mise à jour depuis GitHub..."
git pull origin main

# Attendre un peu
sleep 2

# Lancer l'application
echo "🚀 Lancement de Protein Resequencer..."
./start.sh
