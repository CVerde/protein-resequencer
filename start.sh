#!/bin/bash

cd /home/pi/protein-resequencer || exit 1

# Arrêter les anciennes instances
pkill -f "python3 app.py" 2>/dev/null
pkill -f "chromium.*localhost:5000" 2>/dev/null

sleep 1

# Serveur Flask
python3 app.py &
SERVER_PID=$!

sleep 2

# Chromium kiosque sous Wayland
XDG_RUNTIME_DIR=/run/user/1000 \
WAYLAND_DISPLAY=wayland-0 \
chromium \
  --ozone-platform=wayland \
  --password-store=basic \
  --kiosk \
  --start-fullscreen \
  --touch-events=enabled \
  --disable-pinch \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  http://localhost:5000 &

wait $SERVER_PID
