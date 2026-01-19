#!/usr/bin/env python3
"""
Protein Resequencer - Chambre de Fermentation Contrôlée
Contrôleur principal v2
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import json
import os
import threading
import time

app = Flask(__name__)

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
    "natto": {
        "name": "Natto",
        "icon": "🫘",
        "code": "N",
        "system": True,
        "steps": [
            {"name": "Fermentation", "temp": 42, "humidity": 85, "duration": 24, "ventilation": "off"}
        ]
    },
    "tempeh": {
        "name": "Tempeh",
        "icon": "🟫",
        "code": "T",
        "system": True,
        "steps": [
            {"name": "Préchauffage", "temp": 32, "humidity": 85, "duration": 2, "ventilation": "off"},
            {"name": "Incubation", "temp": 32, "humidity": 85, "duration": 24, "ventilation": "off"},
            {"name": "Maturation", "temp": 30, "humidity": 80, "duration": 10, "ventilation": "cyclic"}
        ]
    },
    "koji_rice": {
        "name": "Koji Riz",
        "icon": "🍚",
        "code": "KR",
        "system": True,
        "steps": [
            {"name": "Germination", "temp": 30, "humidity": 85, "duration": 12, "ventilation": "off"},
            {"name": "Croissance", "temp": 32, "humidity": 80, "duration": 24, "ventilation": "cyclic"},
            {"name": "Sporulation", "temp": 28, "humidity": 75, "duration": 12, "ventilation": "on"}
        ]
    },

    "kombucha": {
        "name": "Kombucha",
        "icon": "🧪",
        "code": "KB",
        "system": True,
        "steps": [
            {"name": "Fermentation", "temp": 26, "humidity": 60, "duration": 168, "ventilation": "off"}
        ]
    },
    "yogurt": {
        "name": "Yaourt",
        "icon": "🥛",
        "code": "Y",
        "system": True,
        "steps": [
            {"name": "Fermentation", "temp": 43, "humidity": 70, "duration": 8, "ventilation": "off"}
        ]
    },
    "kimchi": {
        "name": "Kimchi",
        "icon": "🌶️",
        "code": "KI",
        "system": True,
        "steps": [
            {"name": "Fermentation active", "temp": 20, "humidity": 70, "duration": 48, "ventilation": "off"}
        ]
    },
    "lacto": {
        "name": "Lactoferment.",
        "icon": "🥒",
        "code": "LF",
        "system": True,
        "steps": [
            {"name": "Fermentation", "temp": 22, "humidity": 70, "duration": 72, "ventilation": "off"}
        ]
    },
    "miso": {
        "name": "Miso",
        "icon": "🥣",
        "code": "MI",
        "system": True,
        "steps": [
            {"name": "Fermentation", "temp": 28, "humidity": 75, "duration": 720, "ventilation": "off"}
        ]
    },
    "vinegar": {
        "name": "Vinaigre",
        "icon": "🍯",
        "code": "V",
        "system": True,
        "steps": [
            {"name": "Acétification", "temp": 28, "humidity": 60, "duration": 336, "ventilation": "cyclic"}
        ]
    },
    "dehydrate": {
        "name": "Désydra.",
        "icon": "💨",
        "code": "DH",
        "system": True,
        "steps": [
            {"name": "Séchage", "temp": 45, "humidity": 20, "duration": 12, "ventilation": "on"}
        ]
    },
    "manual": {
        "name": "Manuel",
        "icon": "⚙️",
        "code": "X",
        "system": True,
        "steps": [
            {"name": "Étape 1", "temp": 30, "humidity": 70, "duration": 24, "ventilation": "off"}
        ]
    }
}

# Fichiers de données
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
    return load_json(SETTINGS_FILE, {
        "temp_alert_delay": 20,
        "humidity_tolerance": 10,
        "overheat_threshold": 10,
        "max_temp": 60,
        "initial_phase_no_alert": 2,
        "end_alerts": [120, 60, 30]
    })

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def load_custom_presets():
    return load_json(CUSTOM_PRESETS_FILE, {})

def save_custom_presets(presets):
    save_json(CUSTOM_PRESETS_FILE, presets)

def get_all_presets():
    """Retourne tous les préréglages (système + personnalisés)"""
    custom = load_custom_presets()
    all_presets = {**SYSTEM_PRESETS}
    for key, preset in custom.items():
        all_presets[key] = {**preset, "system": False}
    return all_presets

def read_ds18b20():
    """Lecture des sondes DS18B20 via 1-Wire"""
    temps = []
    w1_path = "/sys/bus/w1/devices/"
    try:
        for device in os.listdir(w1_path):
            if device.startswith("28-"):
                with open(f"{w1_path}{device}/w1_slave", "r") as f:
                    lines = f.readlines()
                    if lines[0].strip().endswith("YES"):
                        pos = lines[1].find("t=")
                        if pos != -1:
                            temp = float(lines[1][pos+2:]) / 1000.0
                            temps.append(temp)
    except Exception as e:
        print(f"Erreur lecture DS18B20: {e}")
    while len(temps) < 3:
        temps.append(0.0)
    return temps[:3]

def read_sht40():
    """Lecture du SHT40 via I2C - À implémenter"""
    # TODO: implémenter avec smbus2 quand branché
    return None, None

def read_sensors():
    """Lecture de tous les capteurs"""
    temps = read_ds18b20()
    state["sensors"]["temperature"] = temps
    
    hum, temp_sht = read_sht40()
    if hum is not None:
        state["sensors"]["humidity"] = hum
        state["sensors"]["temp_sht40"] = temp_sht
    else:
        state["sensors"]["humidity"] = 50.0
        state["sensors"]["temp_sht40"] = sum(temps) / len(temps) if any(temps) else 22.0

def control_actuators():
    """Contrôle des actionneurs basé sur les consignes"""
    if not state["batch"]:
        state["actuators"] = {k: False for k in state["actuators"]}
        return
    
    step = state["batch"]["current_step"]
    avg_temp = sum(state["sensors"]["temperature"]) / 3
    
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

def generate_batch_id(preset_code):
    """Génère un ID de batch unique"""
    history = load_history()
    count = sum(1 for b in history if b.get("preset_code") == preset_code) + 1
    return f"#{preset_code}-{count:04d}"

# Routes API
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
        
        batch_info = {
            **state["batch"],
            "elapsed_hours": round(elapsed_hours, 1),
            "step_progress": round(step_progress, 1),
            "total_elapsed": round(total_elapsed, 1),
            "total_progress": round(total_progress, 1)
        }
    
    return jsonify({
        "batch": batch_info,
        "sensors": state["sensors"],
        "actuators": state["actuators"],
        "mode": state["mode"],
        "events": state["events"][:20],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/presets')
def get_presets():
    return jsonify(get_all_presets())

@app.route('/api/presets/custom', methods=['POST'])
def create_custom_preset():
    data = request.json
    custom = load_custom_presets()
    
    key = data.get('key') or f"custom_{int(time.time())}"
    custom[key] = {
        "name": data.get('name', 'Sans nom'),
        "icon": data.get('icon', '⚙️'),
        "code": data.get('code', 'CU'),
        "parent": data.get('parent'),
        "steps": data.get('steps', []),
        "created_at": datetime.now().isoformat()
    }
    
    save_custom_presets(custom)
    return jsonify({"success": True, "key": key})

@app.route('/api/presets/custom/<key>', methods=['DELETE'])
def delete_custom_preset(key):
    custom = load_custom_presets()
    if key in custom:
        del custom[key]
        save_custom_presets(custom)
        return jsonify({"success": True})
    return jsonify({"error": "Préréglage non trouvé"}), 404

@app.route('/api/history')
def get_history():
    history = load_history()
    sort_by = request.args.get('sort', 'date')
    filter_type = request.args.get('type')
    filter_status = request.args.get('status')
    
    if filter_type:
        history = [h for h in history if h.get('preset_code') == filter_type]
    if filter_status:
        history = [h for h in history if h.get('status') == filter_status]
    
    if sort_by == 'date':
        history.sort(key=lambda x: x.get('started_at', ''), reverse=True)
    elif sort_by == 'name':
        history.sort(key=lambda x: x.get('name', ''))
    elif sort_by == 'type':
        history.sort(key=lambda x: x.get('preset_code', ''))
    elif sort_by == 'rating':
        history.sort(key=lambda x: x.get('rating', 0), reverse=True)
    
    return jsonify(history)

@app.route('/api/history/<batch_id>', methods=['GET'])
def get_history_item(batch_id):
    history = load_history()
    for h in history:
        if h.get('id') == batch_id:
            return jsonify(h)
    return jsonify({"error": "Batch non trouvé"}), 404

@app.route('/api/history/<batch_id>', methods=['DELETE'])
def delete_history_item(batch_id):
    history = load_history()
    history = [h for h in history if h.get('id') != batch_id]
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
    return jsonify({"error": "Batch non trouvé"}), 404

@app.route('/api/batch/start', methods=['POST'])
def start_batch():
    data = request.json
    
    steps = data.get('steps')
    preset_key = data.get('preset')
    preset_code = data.get('code', 'X')
    preset_name = data.get('name', 'Manuel')
    
    if not steps and preset_key:
        presets = get_all_presets()
        preset = presets.get(preset_key)
        if not preset:
            return jsonify({"error": "Preset inconnu"}), 400
        steps = preset["steps"]
        preset_code = preset["code"]
        preset_name = preset["name"]
    
    if not steps:
        return jsonify({"error": "Aucune étape définie"}), 400
    
    batch_id = generate_batch_id(preset_code)
    now = datetime.now()
    total_duration = sum(s["duration"] for s in steps)
    
    state["batch"] = {
        "id": batch_id,
        "name": data.get('name', preset_name),
        "preset": preset_key,
        "preset_code": preset_code,
        "steps": steps,
        "current_step_index": 0,
        "current_step": steps[0],
        "started_at": now.isoformat(),
        "step_started_at": now.isoformat(),
        "total_duration": total_duration,
        "ingredients": data.get('ingredients', [])
    }
    state["mode"] = "dehydrating" if preset_key == "dehydrate" else "fermenting"
    state["events"] = [{
        "time": now.isoformat(),
        "text": f"Démarrage {preset_name}"
    }]
    
    return jsonify({"success": True, "batch": state["batch"]})

@app.route('/api/batch/stop', methods=['POST'])
def stop_batch():
    data = request.json or {}
    
    if state["batch"]:
        history = load_history()
        batch_record = {
            **state["batch"],
            "ended_at": datetime.now().isoformat(),
            "events": state["events"],
            "status": data.get('status', 'completed'),
            "rating": data.get('rating', 0),
            "notes": data.get('notes', '')
        }
        history.insert(0, batch_record)
        save_history(history)
        
        state["batch"] = None
        state["mode"] = "idle"
        state["events"] = []
    
    return jsonify({"success": True})

@app.route('/api/batch/next-step', methods=['POST'])
def next_step():
    if not state["batch"]:
        return jsonify({"error": "Aucun batch en cours"}), 400
    
    current_idx = state["batch"]["current_step_index"]
    steps = state["batch"]["steps"]
    
    if current_idx + 1 >= len(steps):
        return jsonify({"error": "Dernière étape atteinte"}), 400
    
    state["batch"]["current_step_index"] = current_idx + 1
    state["batch"]["current_step"] = steps[current_idx + 1]
    state["batch"]["step_started_at"] = datetime.now().isoformat()
    
    state["events"].insert(0, {
        "time": datetime.now().isoformat(),
        "text": f"Passage à l'étape: {steps[current_idx + 1]['name']}"
    })
    
    return jsonify({"success": True, "step": state["batch"]["current_step"]})

@app.route('/api/batch/event', methods=['POST'])
def add_event():
    data = request.json
    event = {
        "time": datetime.now().isoformat(),
        "text": data.get('text', '')
    }
    state["events"].insert(0, event)
    return jsonify({"success": True, "event": event})

@app.route('/api/actuator/<name>', methods=['POST'])
def toggle_actuator(name):
    if name in state["actuators"]:
        data = request.json or {}
        if 'state' in data:
            state["actuators"][name] = data['state']
        else:
            state["actuators"][name] = not state["actuators"][name]
        return jsonify({"success": True, "state": state["actuators"][name]})
    return jsonify({"error": "Actionneur inconnu"}), 400

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        save_settings(request.json)
        return jsonify({"success": True})
    return jsonify(load_settings())

@app.route('/api/quit', methods=['POST'])
def quit_app():
    """Arrête le serveur et l'application"""
    import subprocess
    subprocess.Popen(['pkill', '-f', 'chromium.*localhost:5000'])
    subprocess.Popen(['pkill', '-f', 'onboard'])
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    else:
        os._exit(0)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
