#!/bin/bash
# Protein Resequencer Launcher

cd /home/pi/protein-resequencer

# Arrêter les instances précédentes
pkill -f "python3 app.py" 2>/dev/null
pkill -f "chromium.*localhost:5000" 2>/dev/null
pkill -f "wvkbd" 2>/dev/null
pkill -f "onboard" 2>/dev/null
pkill -f "squeekboard" 2>/dev/null

sleep 1

# Lancer le serveur Flask en arrière-plan
python3 app.py &
SERVER_PID=$!

# Attendre que le serveur démarre
sleep 2

# Lancer le clavier virtuel (essayer plusieurs options)
if command -v wvkbd-mobintl &> /dev/null; then
    wvkbd-mobintl -L 300 &
elif command -v squeekboard &> /dev/null; then
    DISPLAY=:0 squeekboard &
elif command -v onboard &> /dev/null; then
    DISPLAY=:0 onboard &
fi

sleep 1

# Lancer Chromium en mode kiosque
DISPLAY=:0 chromium --kiosk \
    --start-fullscreen \
    --touch-events=enabled \
    --enable-features=VirtualKeyboardInputMode \
    --disable-pinch \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    http://localhost:5000 &

wait $SERVER_PID