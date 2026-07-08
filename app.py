#!/usr/bin/env python3
"""
Protein Resequencer - Chambre de Fermentation Contrôlée
Contrôleur principal v4 - GPIO relais, HACCP frigo
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from collections import deque
import json
import os
import threading
import time

app = Flask(__name__)

# GPIO relay mapping
RELAY_PINS = {
    "fan_internal": 17,   # M1
    "fan_extract": 27,    # M2
    "humidifier": 22,     # M3
    "heater": 23,         # M4 -> SSR
}

# Sondes DS18B20 par adresse
SENSOR_MAP = {
    "28-0000007020af": "t1",  # chambre
    "28-00000071b49c": "t2",  # chambre
    "28-00000073a825": "t3",  # frigo HACCP
}
HACCP_LOG_FILE = "haccp.json"
HACCP_INTERVAL = 900  # 15 min entre chaque relevé

# Init GPIO
gpio_available = False
relay_lines = {}
try:
    from gpiozero import OutputDevice
    for name, pin in RELAY_PINS.items():
        relay_lines[name] = OutputDevice(pin, active_high=True, initial_value=True)
    gpio_available = True
    print("GPIO initialisé (gpiozero)")
except Exception as e:
    print(f"GPIO non disponible: {e}")

def set_relay(name, state_on):
    if name in relay_lines:
        if state_on:
            relay_lines[name].off()   # LOW = relay ON
        else:
            relay_lines[name].on()    # HIGH = relay OFF

# Historique des capteurs (stockage en mémoire)
SENSOR_HISTORY_MAX = 3600  # 1h de données à 1s = 3600 points
sensor_history = {
    "timestamps": deque(maxlen=SENSOR_HISTORY_MAX),
    "t1": deque(maxlen=SENSOR_HISTORY_MAX),
    "t2": deque(maxlen=SENSOR_HISTORY_MAX),
    "t3": deque(maxlen=SENSOR_HISTORY_MAX),
    "humidity": deque(maxlen=SENSOR_HISTORY_MAX)
}

# État global du système
state = {
    "batch": None,
    "sensors": {
        "temperature": [0.0, 0.0, 0.0],
        "humidity": 0.0,
        "temp_sht40": 0.0
    },
    "actuators": {
        "heater": False,
        "humidifier": False,
        "fan_internal": False,
        "fan_extract": False
    },
    "mode": "idle",
    "events": []
}

# Préréglages de fermentation (système)
SYSTEM_PRESETS = {
    "natto": {"name": "Natto", "icon": "N", "code": "N", "system": True,
        "steps": [{"name": "Fermentation", "temp": 42, "humidity": 85, "duration": 24, "ventilation": "off"}]},
    "tempeh": {"name": "Tempeh", "icon": "T", "code": "T", "system": True,
        "steps": [{"name": "Préchauffage", "temp": 32, "humidity": 85, "duration": 2, "ventilation": "off"},
                  {"name": "Incubation", "temp": 32, "humidity": 85, "duration": 24, "ventilation": "off"},
                  {"name": "Maturation", "temp": 30, "humidity": 80, "duration": 10, "ventilation": "cyclic"}]},
    "koji_rice": {"name": "Koji Riz", "icon": "KR", "code": "KR", "system": True,
        "steps": [{"name": "Germination", "temp": 30, "humidity": 85, "duration": 12, "ventilation": "off"},
                  {"name": "Croissance", "temp": 32, "humidity": 80, "duration": 24, "ventilation": "cyclic"},
                  {"name": "Sporulation", "temp": 28, "humidity": 75, "duration": 12, "ventilation": "on"}]},
    "kombucha": {"name": "Kombucha", "icon": "KB", "code": "KB", "system": True,
        "steps": [{"name": "Fermentation", "temp": 26, "humidity": 60, "duration": 168, "ventilation": "off"}]},
    "yogurt": {"name": "Yaourt", "icon": "Y", "code": "Y", "system": True,
        "steps": [{"name": "Fermentation", "temp": 43, "humidity": 70, "duration": 8, "ventilation": "off"}]},
    "kimchi": {"name": "Kimchi", "icon": "KI", "code": "KI", "system": True,
        "steps": [{"name": "Fermentation active", "temp": 20, "humidity": 70, "duration": 48, "ventilation": "off"}]},
    "lacto": {"name": "Lactoferment.", "icon": "LF", "code": "LF", "system": True,
        "steps": [{"name": "Fermentation", "temp": 22, "humidity": 70, "duration": 72, "ventilation": "off"}]},
    "miso": {"name": "Miso", "icon": "MI", "code": "MI", "system": True,
        "steps": [{"name": "Fermentation", "temp": 28, "humidity": 75, "duration": 720, "ventilation": "off"}]},
    "vinegar": {"name": "Vinaigre", "icon": "V", "code": "V", "system": True,
        "steps": [{"name": "Acétification", "temp": 28, "humidity": 60, "duration": 336, "ventilation": "cyclic"}]},
    "dehydrate": {"name": "Déshydra.", "icon": "DH", "code": "DH", "system": True,
        "steps": [{"name": "Séchage", "temp": 45, "humidity": 20, "duration": 12, "ventilation": "on"}]},
    "manual": {"name": "Manuel", "icon": "M", "code": "X", "system": True,
        "steps": [{"name": "Étape 1", "temp": 30, "humidity": 70, "duration": 24, "ventilation": "off"}]}
}

HISTORY_FILE = "history.json"
SETTINGS_FILE = "settings.json"
CUSTOM_PRESETS_FILE = "custom_presets.json"

def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_history():
    return load_json(HISTORY_FILE, [])

def save_history(history):
    save_json(HISTORY_FILE, history)

def load_settings():
    return load_json(SETTINGS_FILE, {"temp_alert_delay": 20, "humidity_tolerance": 10})

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def load_custom_presets():
    return load_json(CUSTOM_PRESETS_FILE, {})

def save_custom_presets(presets):
    save_json(CUSTOM_PRESETS_FILE, presets)

def get_all_presets():
    custom = load_custom_presets()
    all_presets = {**SYSTEM_PRESETS}
    for key, preset in custom.items():
        all_presets[key] = {**preset, "system": False}
    return all_presets

def read_ds18b20():
    result = {"t1": 0.0, "t2": 0.0, "t3": 0.0}
    w1_path = "/sys/bus/w1/devices/"
    try:
        for device in os.listdir(w1_path):
            if device.startswith("28-") and device in SENSOR_MAP:
                with open(f"{w1_path}{device}/w1_slave", "r") as f:
                    lines = f.readlines()
                    if lines[0].strip().endswith("YES"):
                        pos = lines[1].find("t=")
                        if pos != -1:
                            temp = float(lines[1][pos+2:]) / 1000.0
                            result[SENSOR_MAP[device]] = round(temp, 1)
    except Exception as e:
        print(f"Erreur DS18B20: {e}")
    return [result["t1"], result["t2"], result["t3"]]

def read_sht40():
    try:
        import board
        import adafruit_sht4x
        sht = adafruit_sht4x.SHT4x(board.I2C())
        return sht.relative_humidity, sht.temperature
    except Exception as e:
        print(f"SHT40 error: {e}")
        return None, None

def read_sensors():
    temps = read_ds18b20()
    state["sensors"]["temperature"] = temps
    state["sensors"]["fridge_temp"] = temps[2]  # T3 = frigo
    hum, temp_sht = read_sht40()
    if hum is not None:
        state["sensors"]["humidity"] = hum
        state["sensors"]["temp_sht40"] = temp_sht
    else:
        state["sensors"]["humidity"] = 50.0
        state["sensors"]["temp_sht40"] = sum(temps[:2]) / 2 if any(temps[:2]) else 22.0
    
    # Log HACCP frigo
    if temps[2] > 0:
        log_haccp(temps[2])
    
    # Enregistrer dans l'historique
    now = datetime.now().isoformat()
    sensor_history["timestamps"].append(now)
    sensor_history["t1"].append(temps[0])
    sensor_history["t2"].append(temps[1])
    sensor_history["t3"].append(temps[2])
    sensor_history["humidity"].append(state["sensors"]["humidity"])

def control_actuators():
    if not state["batch"]:
        if not state.get("manual_override"):
            for k in state["actuators"]:
                state["actuators"][k] = False
                set_relay(k, False)
        return
    step = state["batch"]["current_step"]
    temps = state["sensors"]["temperature"]
    avg_temp = (temps[0] + temps[1]) / 2 if (temps[0] and temps[1]) else (temps[0] or temps[1] or 22.0)
    state["actuators"]["heater"] = avg_temp < step["temp"] - 0.5
    state["actuators"]["humidifier"] = state["sensors"]["humidity"] < step["humidity"] - 5
    if step["ventilation"] == "on":
        state["actuators"]["fan_internal"] = True
        state["actuators"]["fan_extract"] = state["mode"] == "dehydrating"
    elif step["ventilation"] == "cyclic":
        cycle = int(time.time() / 60) % 15
        state["actuators"]["fan_internal"] = cycle < 5
        state["actuators"]["fan_extract"] = False
    else:
        state["actuators"]["fan_internal"] = False
        state["actuators"]["fan_extract"] = False
    for k, v in state["actuators"].items():
        set_relay(k, v)

# HACCP frigo — relevés aux heures fixes (0, 3, 6, 9, 12, 15, 18, 21)
HACCP_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]
last_haccp_hour = -1
def log_haccp(fridge_temp):
    global last_haccp_hour
    now = datetime.now()
    current_hour = now.hour
    if current_hour not in HACCP_HOURS:
        return
    if current_hour == last_haccp_hour:
        return
    last_haccp_hour = current_hour
    entry = {"time": now.isoformat(), "temp": fridge_temp}
    try:
        data = load_json(HACCP_LOG_FILE, [])
        data.append(entry)
        # Garder 90 jours
        cutoff = (now - timedelta(days=90)).isoformat()
        data = [e for e in data if e["time"] > cutoff]
        save_json(HACCP_LOG_FILE, data)
    except Exception as e:
        print(f"HACCP log error: {e}")

def generate_batch_id(preset_code):
    history = load_history()
    count = sum(1 for b in history if b.get("preset_code") == preset_code) + 1
    return f"#{preset_code}-{count:04d}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state():
    read_sensors()
    control_actuators()
    batch_info = None
    if state["batch"]:
        step = state["batch"]["current_step"]
        step_start = datetime.fromisoformat(state["batch"]["step_started_at"])
        elapsed_hours = (datetime.now() - step_start).total_seconds() / 3600
        step_progress = min(100, (elapsed_hours / step["duration"]) * 100)
        total_start = datetime.fromisoformat(state["batch"]["started_at"])
        total_elapsed = (datetime.now() - total_start).total_seconds() / 3600
        total_progress = min(100, (total_elapsed / state["batch"]["total_duration"]) * 100)
        batch_info = {**state["batch"], "elapsed_hours": round(elapsed_hours, 1),
            "step_progress": round(step_progress, 1), "total_elapsed": round(total_elapsed, 1),
            "total_progress": round(total_progress, 1)}
    return jsonify({"batch": batch_info, "sensors": state["sensors"], "actuators": state["actuators"],
        "mode": state["mode"], "events": state["events"][:20], "timestamp": datetime.now().isoformat()})

@app.route('/api/sensors/history')
def get_sensor_history():
    interval = request.args.get('interval', '1m')
    # Calculer le pas d'échantillonnage
    if interval == '15m':
        step = 15
    elif interval == '1h':
        step = 60
    else:
        step = 1
    
    timestamps = list(sensor_history["timestamps"])
    t1 = list(sensor_history["t1"])
    t2 = list(sensor_history["t2"])
    t3 = list(sensor_history["t3"])
    humidity = list(sensor_history["humidity"])
    
    # Sous-échantillonner
    if step > 1 and len(timestamps) > step:
        timestamps = timestamps[::step]
        t1 = t1[::step]
        t2 = t2[::step]
        t3 = t3[::step]
        humidity = humidity[::step]
    
    return jsonify({
        "timestamps": timestamps[-60:],  # 60 derniers points
        "t1": t1[-60:],
        "t2": t2[-60:],
        "t3": t3[-60:],
        "humidity": humidity[-60:]
    })

@app.route('/api/presets')
def get_presets():
    return jsonify(get_all_presets())

@app.route('/api/presets/custom', methods=['POST'])
def create_custom_preset():
    data = request.json
    custom = load_custom_presets()
    key = data.get('key') or f"custom_{int(time.time())}"
    custom[key] = {"name": data.get('name', 'Sans nom'), "icon": "C", "code": "CU",
        "parent": data.get('parent'), "steps": data.get('steps', []), "created_at": datetime.now().isoformat()}
    save_custom_presets(custom)
    return jsonify({"success": True, "key": key})

@app.route('/api/presets/custom/<key>', methods=['DELETE'])
def delete_custom_preset(key):
    custom = load_custom_presets()
    if key in custom:
        del custom[key]
        save_custom_presets(custom)
        return jsonify({"success": True})
    return jsonify({"error": "Non trouvé"}), 404

@app.route('/api/history')
def get_history():
    history = load_history()
    history.sort(key=lambda x: x.get('started_at', ''), reverse=True)
    return jsonify(history)

@app.route('/api/history/<batch_id>', methods=['GET'])
def get_history_item(batch_id):
    for h in load_history():
        if h.get('id') == batch_id:
            return jsonify(h)
    return jsonify({"error": "Non trouvé"}), 404

@app.route('/api/history/<batch_id>', methods=['DELETE'])
def delete_history_item(batch_id):
    history = [h for h in load_history() if h.get('id') != batch_id]
    save_history(history)
    return jsonify({"success": True})

@app.route('/api/history/<batch_id>/rating', methods=['POST'])
def rate_history_item(batch_id):
    data = request.json
    history = load_history()
    for h in history:
        if h.get('id') == batch_id:
            h['rating'] = data.get('rating', 0)
            h['status'] = data.get('status', h.get('status'))
            h['notes'] = data.get('notes', h.get('notes', ''))
            save_history(history)
            return jsonify({"success": True})
    return jsonify({"error": "Non trouvé"}), 404

@app.route('/api/batch/start', methods=['POST'])
def start_batch():
    data = request.json
    steps = data.get('steps')
    preset_key = data.get('preset')
    preset_code = data.get('code', 'X')
    preset_name = data.get('name', 'Manuel')
    if not steps and preset_key:
        preset = get_all_presets().get(preset_key)
        if not preset:
            return jsonify({"error": "Preset inconnu"}), 400
        steps = preset["steps"]
        preset_code = preset["code"]
        preset_name = preset["name"]
    if not steps:
        return jsonify({"error": "Aucune étape"}), 400
    batch_id = generate_batch_id(preset_code)
    now = datetime.now()
    state["batch"] = {"id": batch_id, "name": data.get('name', preset_name), "preset": preset_key,
        "preset_code": preset_code, "steps": steps, "current_step_index": 0, "current_step": steps[0],
        "started_at": now.isoformat(), "step_started_at": now.isoformat(),
        "total_duration": sum(s["duration"] for s in steps)}
    state["mode"] = "dehydrating" if preset_key == "dehydrate" else "fermenting"
    state["events"] = [{"time": now.isoformat(), "text": f"Démarrage {preset_name}"}]
    return jsonify({"success": True, "batch": state["batch"]})

@app.route('/api/batch/stop', methods=['POST'])
def stop_batch():
    data = request.json or {}
    if state["batch"]:
        history = load_history()
        # Sauvegarder l'historique des capteurs avec le batch
        batch_sensor_history = {
            "timestamps": list(sensor_history["timestamps"]),
            "t1": list(sensor_history["t1"]),
            "t2": list(sensor_history["t2"]),
            "t3": list(sensor_history["t3"]),
            "humidity": list(sensor_history["humidity"])
        }
        history.insert(0, {**state["batch"], "ended_at": datetime.now().isoformat(),
            "events": state["events"], "status": data.get('status', 'completed'),
            "rating": data.get('rating', 0), "notes": data.get('notes', ''),
            "sensor_history": batch_sensor_history})
        save_history(history)
        state["batch"] = None
        state["mode"] = "idle"
        state["events"] = []
        # Vider l'historique des capteurs pour le prochain batch
        for key in sensor_history:
            sensor_history[key].clear()
    return jsonify({"success": True})

@app.route('/api/batch/next-step', methods=['POST'])
def next_step():
    if not state["batch"]:
        return jsonify({"error": "Aucun batch"}), 400
    idx = state["batch"]["current_step_index"]
    steps = state["batch"]["steps"]
    if idx + 1 >= len(steps):
        return jsonify({"error": "Dernière étape"}), 400
    state["batch"]["current_step_index"] = idx + 1
    state["batch"]["current_step"] = steps[idx + 1]
    state["batch"]["step_started_at"] = datetime.now().isoformat()
    state["events"].insert(0, {"time": datetime.now().isoformat(), "text": f"Étape: {steps[idx + 1]['name']}"})
    return jsonify({"success": True, "step": state["batch"]["current_step"]})

@app.route('/api/batch/event', methods=['POST'])
def add_event():
    data = request.json
    event = {"time": datetime.now().isoformat(), "text": data.get('text', '')}
    state["events"].insert(0, event)
    return jsonify({"success": True, "event": event})

@app.route('/api/actuator/<name>', methods=['POST'])
def toggle_actuator(name):
    if name in state["actuators"]:
        data = request.json or {}
        state["actuators"][name] = data.get('state', not state["actuators"][name])
        set_relay(name, state["actuators"][name])
        # Activer mode manuel si pas de batch
        if not state["batch"]:
            state["manual_override"] = any(state["actuators"].values())
        return jsonify({"success": True, "state": state["actuators"][name]})
    return jsonify({"error": "Inconnu"}), 400

@app.route('/api/pwm/<name>', methods=['POST'])
def set_pwm(name):
    data = request.json or {}
    value = data.get('value', 0)
    # TODO: PWM réel via MOSFET + GPIO hardware PWM
    # Quand MOSFET installé:
    # import pigpio
    # pi = pigpio.pi()
    # pi.set_PWM_dutycycle(PWM_PIN, int(value * 2.55))
    print(f"PWM {name}: {value}%")
    return jsonify({"success": True, "name": name, "value": value})

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        save_settings(request.json)
        return jsonify({"success": True})
    return jsonify(load_settings())

@app.route('/api/quit', methods=['POST'])
def quit_app():
    import subprocess
    subprocess.Popen(['pkill', '-f', 'chromium.*localhost:5000'])
    os._exit(0)
    return jsonify({"success": True})

@app.route('/api/haccp')
def get_haccp():
    data = load_json(HACCP_LOG_FILE, [])
    day = request.args.get('day')  # format YYYY-MM-DD
    if day:
        data = [e for e in data if e["time"].startswith(day)]
    month = request.args.get('month')  # format YYYY-MM
    if month:
        data = [e for e in data if e["time"].startswith(month)]
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
