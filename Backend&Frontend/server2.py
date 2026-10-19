import threading, time, json, queue, os
import random
from datetime import datetime
from flask import Flask, Response, jsonify, request, render_template, render_template_string
from flask_cors import CORS
import requests, cv2, numpy as np
from ultralytics import YOLO
import yt_dlp
from werkzeug.utils import secure_filename

# ============== CONFIGURATION DES SOURCES VIDÉO ==============
# ... vos imports ...




# === NOUVELLE FONCTION DE TÉLÉCHARGEMENT AUTOMATIQUE ===
# === FONCTION DE TÉLÉCHARGEMENT CORRIGÉE ===
# === VERSION CORRIGÉE : TÉLÉCHARGEMENT VIA YOUTUBE (PLUS STABLE) ===
# === FONCTION SIMPLIFIÉE : VÉRIFICATION SEULEMENT ===
def download_test_video():
    # Chemin du fichier
    local_filename = os.path.join("uploads", "test_pompier.mp4")
    
    # On vérifie juste si le fichier est là
    if os.path.exists(local_filename) and os.path.getsize(local_filename) > 0:
        print(f"✅ Vidéo de test trouvée : {local_filename}")
        return local_filename

    # S'il n'est pas là, on prévient juste l'utilisateur
    print("---------------------------------------------------")
    print("⚠️  FICHIER MANQUANT : test_pompier.mp4")
    print("👉  Veuillez télécharger une vidéo de pompier manuellement,")
    print("    la renommer 'test_pompier.mp4' et la mettre dans le dossier 'uploads'.")
    print("---------------------------------------------------")
    return None


# ========================================================

# ... la suite du code ...
# 1. SOURCE PRINCIPALE (Surveillance Trafic Live)
# Vidéo de trafic dense à Ho Chi Minh City (Parfait pour compter les voitures)
LIVE_SURVEILLANCE_URL = "https://www.youtube.com/watch?v=1EiC9bvVGnk" 

# 2. SOURCE TEST IA (Scénario Urgence)
# Vidéo avec Camion Pompier (Pour déclencher l'alerte "Ambulance/Truck")
TEST_SCENARIO_PATH = os.path.join("uploads", "test_pompier.mp4")

# --- VARIABLES GLOBALES DE GESTION ---
# Au démarrage, on utilise la surveillance live
current_video_source = LIVE_SURVEILLANCE_URL 
video_source_changed = False
is_youtube_source = True

# Paramètres Vidéo & IA
FRAME_WIDTH, FRAME_HEIGHT = 640, 360
PROCESS_EVERY_N_FRAMES = 3
DETECTION_CONFIDENCE = 0.3
YOLO_MODEL_PATH = "yolov8n.pt"

# Configuration IA & API
DEEPSEEK_API = "http://localhost:11434/api/generate"
DEEPSEEK_MODEL = "llama3.2:latest"  # [MODIF 3] modèle Ollama installé (llama3.2)

# --- CLÉ GOOGLE MAPS ---
GOOGLE_MAPS_API_KEY = "AIzaSyB58-MhTUUDP5DBNeAkNkyVdqchJQkvFT8"

# [MODIF 1] URL de PRODUCTION n8n (workflow activé). Pour tester avec "Listen for test event",
# lance le script avec : set N8N_WEBHOOK_URL=http://localhost:5678/webhook-test/traffic-alert
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/traffic-alert")
N8N_ENABLED = os.getenv("N8N_ENABLED", "true").lower() == "true"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============== ÉTAT GLOBAL ==============
state = {
    "control_mode": "manual",
    "traffic_detection_active": False,
    "timer_active": False,
    "pause_active": False,
    "last_stats": {"cars": 0, "buses": 0, "trucks": 0, "pedestrians": 0},
    "running": True,
    "current_traffic_light": 1,
    "incidents": [],
    "traffic_history": [],
}

LED_STATE = { "red1": False, "red2": False, "yellow1": False, "yellow2": False, "green1": False, "green2": False }
ARDUINO_COMMAND_BUFFER = []
TIMER_CONFIG = { "yellow_transition": 4, "green_duration": 5 }
MAP_CONFIG = {
    "center": {"lat": 33.2585, "lng": -8.5087},
    "lights": [
        {"id": 1, "name": "Feu 1 - Av. Mohamed VI", "position": {"lat": 33.2587, "lng": -8.5089}},
        {"id": 2, "name": "Feu 2 - Rue El Khattabi", "position": {"lat": 33.2584, "lng": -8.5084}},
    ],
}

frame_queue = queue.Queue(maxsize=1)
yolo = None
app = Flask(__name__)
CORS(app)

# ============== FONCTIONS UTILITAIRES ==============
def extract_youtube_stream(url):
    if not isinstance(url, str): return url
    # Si c'est un chiffre, c'est la webcam
    if isinstance(url, int) or (isinstance(url, str) and url.isdigit()): return int(url)
    
    print(f"⏳ Extraction YouTube en cours pour : {url}")
    
    # Options optimisées pour éviter les blocages "Video unavailable"
    ydl_opts = {
        "quiet": True, 
        "no_warnings": True,
        "format": "230", # Force MP4
        "noplaylist": True,
        "geo_bypass": True, # Tente de contourner le blocage géographique
        "ignoreerrors": True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                print("❌ Erreur: Vidéo introuvable ou restreinte.")
                return 0 # Retour webcam
                
            url_stream = info.get("url", None)
            print("✅ Lien stream extrait avec succès !")
            return url_stream
            
    except Exception as e:
        print(f"❌ Erreur yt_dlp critique : {e}")
        return 0 # En cas d'erreur, retour webcam

def send_n8n_notification(event_type, data):
    if not N8N_ENABLED or not N8N_WEBHOOK_URL: return
    # [MODIF 2] Le workflow n8n (SMS textbee + WhatsApp) ne gère que ces 2 alertes.
    # On n'envoie plus "light_switch", sinon un SMS/WhatsApp partirait à chaque changement de feu.
    if event_type not in ("ambulance_detected", "congestion_detected"): return
    try:
        payload = {"timestamp": datetime.now().isoformat(), "event_type": event_type, "data": data}
        threading.Thread(target=requests.post, args=(N8N_WEBHOOK_URL,), kwargs={"json": payload, "timeout": 5}).start()
    except Exception as e: print(f"[N8N] Error: {e}")

# [MODIF 4] Fonction manquante : envoie la question à Ollama (llama3.2) et renvoie la réponse
def ask_deepseek(prompt):
    try:
        r = requests.post(DEEPSEEK_API, json={
            "model": DEEPSEEK_MODEL,
            "prompt": "Réponds en français, de façon courte et claire. Question : " + prompt,
            "stream": False
        }, timeout=60)
        text = r.json().get("response", "")
        return text.split("</think>")[-1].strip()
    except Exception as e:
        print(f"[OLLAMA] Erreur : {e}")
        return None

def update_arduino_leds():
    global ARDUINO_COMMAND_BUFFER
    commands = []
    for led, is_on in LED_STATE.items():
        commands.append(f"{led}_{'on' if is_on else 'off'}")
    ARDUINO_COMMAND_BUFFER = commands
    return commands

# ============== LOGIQUE TRAFIC ==============
def switch_traffic_light(target_light):
    if target_light == 1:
        LED_STATE.update({"red1": True, "yellow1": False, "green1": False, "red2": False, "yellow2": True, "green2": False})
        update_arduino_leds(); time.sleep(TIMER_CONFIG["yellow_transition"])
        LED_STATE.update({"red1": False, "yellow1": False, "green1": True, "red2": True, "yellow2": False, "green2": False})
        state["current_traffic_light"] = 1
    else: 
        LED_STATE.update({"red1": False, "yellow1": True, "green1": False, "red2": True, "yellow2": False, "green2": False})
        update_arduino_leds(); time.sleep(TIMER_CONFIG["yellow_transition"])
        LED_STATE.update({"red1": True, "yellow1": False, "green1": False, "red2": False, "yellow2": False, "green2": True})
        state["current_traffic_light"] = 2
    update_arduino_leds()
    send_n8n_notification("light_switch", {"target_light": target_light})

def pause_traffic_lights():
    state["pause_active"] = True
    LED_STATE.update({"red1": False, "yellow1": True, "green1": False, "red2": False, "yellow2": True, "green2": False})
    update_arduino_leds()

def resume_traffic_lights():
    state["pause_active"] = False
    target = state["current_traffic_light"]
    if target == 1: LED_STATE.update({"red1": False, "yellow1": False, "green1": True, "red2": True, "yellow2": False, "green2": False})
    else: LED_STATE.update({"red1": True, "yellow1": False, "green1": False, "red2": False, "yellow2": False, "green2": True})
    update_arduino_leds()

def decide_traffic_command(stats):
    vehicles = stats.get("cars", 0) + stats.get("buses", 0) + stats.get("trucks", 0)
    state["traffic_history"].append({"timestamp": datetime.now().isoformat(), "vehicles": vehicles, "stats": stats.copy()})
    if len(state["traffic_history"]) > 100: state["traffic_history"] = state["traffic_history"][-100:]
    if vehicles > 10: switch_traffic_light(2 if state["current_traffic_light"] == 1 else 1)

# ============== THREADS & YOLO ==============
def create_incident_internal(type_inc, location, severity):
    new_id = random.randint(10000, 99999)
    inc = { "id": new_id, "type": type_inc, "location": location, "timestamp": datetime.now().isoformat(), "severity": severity, "source": "AI_VIDEO", "coordinates": MAP_CONFIG["center"] }
    state["incidents"].append(inc)
    return inc

def yolo_loop(initial_stream=None):
    global yolo, current_video_source, video_source_changed, is_youtube_source
    
    # Init
    current_video_source = initial_stream if initial_stream else 0
    real_stream_url = (
    extract_youtube_stream(current_video_source)
    if isinstance(current_video_source, str)
    and "youtube.com" in current_video_source
    else current_video_source
    )
    cap = cv2.VideoCapture(real_stream_url)
    
    last_alert_time = 0
    COOLDOWN_ALERT = 20 # On augmente un peu le délai pour éviter de spammer N8N
    idx = 0

    while state["running"]:
        if video_source_changed:
            print(f"🔄 Changement de source demandé : {current_video_source}")
            cap.release()
            if isinstance(current_video_source, str) and "http" in current_video_source and "youtube" in current_video_source:
                real_stream_url = extract_youtube_stream(current_video_source)
            else:
                real_stream_url = current_video_source
            cap = cv2.VideoCapture(real_stream_url)
            video_source_changed = False
            print("✅ Source chargée !")

        ret, frame = cap.read()
        if not ret:
            if isinstance(current_video_source, str):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                time.sleep(1); continue

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        try:
            _, jpeg = cv2.imencode('.jpg', frame)
            if frame_queue.full(): 
                try: frame_queue.get_nowait()
                except: pass
            frame_queue.put(jpeg.tobytes())
        except: pass

        if idx % PROCESS_EVERY_N_FRAMES == 0 and yolo:
            try:
                results = yolo(frame, verbose=False, conf=DETECTION_CONFIDENCE)[0]
                counts = {"cars": 0, "buses": 0, "trucks": 0, "motorcycles": 0, "pedestrians": 0}
                
                for box in results.boxes:
                    cls = int(box.cls)
                    name = yolo.names.get(cls, str(cls))
                    conf = float(box.conf)
                    color = (255, 255, 255); detected = False; label = f"{name} {conf:.2f}"

                    if name == "person":
                        counts["pedestrians"] += 1; color = (0, 0, 255); detected = True
                    elif name in ["car", "taxi"]:
                        counts["cars"] += 1; color = (0, 255, 0); detected = True
                    elif name == "bus":
                        counts["buses"] += 1; color = (0, 255, 255); detected = True
                    elif name == "truck": 
                        counts["trucks"] += 1; color = (255, 0, 0); label = "URGENCE/TRUCK"; detected = True
                        
                    if detected:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # ================= ALERTES N8N & INCIDENTS =================
                current_time = time.time()
                if current_time - last_alert_time > COOLDOWN_ALERT:
                    
                    # CAS 1 : AMBULANCE / POMPIER
                    if counts["trucks"] > 0 or counts["buses"] > 0:
                        print("🚨 ALERTE : AMBULANCE/POMPIER DÉTECTÉ -> ENVOI N8N")
                        create_incident_internal("Ambulance", "Passage véhicule prioritaire", "high")
                        
                        send_n8n_notification("ambulance_detected", {
                            "msg": "🚑 Véhicule d'urgence détecté ! Priorité demandée.",
                            "location": "Feu 1",
                            "count": counts
                        })
                        last_alert_time = current_time

                    # CAS 2 : BOUCHON (CONGESTION)
                    elif counts["cars"] >= 8:
                        print("🚨 ALERTE : BOUCHON DÉTECTÉ -> ENVOI N8N")
                        create_incident_internal("Congestion", "Trafic dense", "medium")
                        
                        send_n8n_notification("congestion_detected", {
                            "msg": "🚗 Trafic saturé détecté (+8 voitures).",
                            "location": "Feu 1",
                            "count": counts
                        })
                        last_alert_time = current_time
                # ===========================================================

                state["last_stats"] = counts
                total_vehicles = counts["cars"] + counts["buses"] + counts["trucks"]
                state["traffic_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "vehicles": total_vehicles, 
                    "stats": counts.copy()
                })
                if len(state["traffic_history"]) > 100: 
                    state["traffic_history"] = state["traffic_history"][-100:]

                if state["control_mode"] == "traffic" and state["traffic_detection_active"]:
                    if total_vehicles > 10: 
                        switch_traffic_light(2 if state["current_traffic_light"] == 1 else 1)

            except Exception as e: 
                print(f"Erreur YOLO: {e}")
                pass
        idx += 1
        time.sleep(0.03)
    cap.release()

def timer_loop():
    while state["running"]:
        if state["control_mode"] != "timer" or not state["timer_active"] or state["pause_active"]:
            time.sleep(0.5); continue
        switch_traffic_light(1); time.sleep(TIMER_CONFIG["green_duration"])
        switch_traffic_light(2); time.sleep(TIMER_CONFIG["green_duration"])

def mjpeg_generator():
    while state["running"]:
        try:
            # On attend une image avec un timeout de 1 seconde
            # Si pas d'image (pendant le switch), on ne plante pas, on recommence la boucle
            buf = frame_queue.get(timeout=1.0)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf + b'\r\n')
        except queue.Empty:
            continue # Si la file est vide (chargement), on attend
        except GeneratorExit:
            # Le navigateur a coupé la connexion (changement de page ou refresh)
            # On arrête proprement le générateur pour éviter l'erreur RuntimeError
            break
        except Exception as e:
            print(f"Erreur flux: {e}")
            continue

# ============== ROUTES PAGES (SÉPARATION) ==============
# Chaque item de la sidebar a désormais sa propre route et son propre template.

@app.route("/")
def index():
    return render_template("dashboard.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/control")
def page_control():
    return render_template("control.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/voice")
def page_voice():
    return render_template("voice.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/automatic")
def page_automatic():
    return render_template("automatic.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/map")
def page_map():
    return render_template("map.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/video")
def page_video():
    return render_template("video.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/incidents")
def page_incidents():
    return render_template("incidents.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/analytics")
def page_analytics():
    return render_template("analytics.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/n8n")
def page_n8n():
    return render_template("n8n.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/chat")
def page_chat():
    return render_template("chat.html", api_key=GOOGLE_MAPS_API_KEY)

# ============== ROUTES API (INCHANGÉES) ==============
@app.route("/video_feed")
def video_feed(): return Response(mjpeg_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/status")
def api_status():
    return jsonify({
        "control_mode": state["control_mode"],
        "leds": LED_STATE,
        "stats": state["last_stats"],
        "pause_active": state["pause_active"],
        "current_traffic_light": state["current_traffic_light"],
        "n8n_enabled": N8N_ENABLED
    })

# [MODIF 5] Flux temps réel (SSE) : envoie l'état des feux à toutes les pages dès qu'il change
@app.route("/api/stream")
def api_stream():
    def gen():
        last = None
        while state["running"]:
            snap = json.dumps({
                "leds": LED_STATE,
                "current_traffic_light": state["current_traffic_light"],
                "control_mode": state["control_mode"]
            })
            if snap != last:
                yield f"data: {snap}\n\n"
                last = snap
            time.sleep(0.2)
    return Response(gen(), mimetype="text/event-stream")

# [MODIF 6] Configuration du timer (durées jaune / vert) modifiable depuis la page Automatique
@app.route("/api/timer_config", methods=["GET", "POST"])
def api_timer_config():
    if request.method == "POST":
        data = request.get_json(force=True)
        try:
            y = int(data.get("yellow"))
            g = int(data.get("green"))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Valeurs invalides"}), 400
        if not (1 <= y <= 60 and 1 <= g <= 60):
            return jsonify({"ok": False, "error": "Valeurs entre 1 et 60 secondes"}), 400
        TIMER_CONFIG["yellow_transition"] = y
        TIMER_CONFIG["green_duration"] = g
    return jsonify({"ok": True, "yellow": TIMER_CONFIG["yellow_transition"], "green": TIMER_CONFIG["green_duration"]})

# --- ROUTE SPECIALE POUR CHANGER DE SOURCE ---
@app.route("/api/set_source", methods=["POST"])
def api_set_source():
    global current_video_source, video_source_changed
    data = request.get_json(force=True)
    source_type = data.get("type")
    
    if source_type == "live":
        current_video_source = LIVE_SURVEILLANCE_URL
        print("📺 Passage au Live")
    elif source_type == "test_ambulance":
        # ICI : On utilise le fichier local
        current_video_source = TEST_SCENARIO_PATH
        print(f"🚑 Passage au Scénario Ambulance (Local: {current_video_source})")
    elif source_type == "webcam":
        current_video_source = 0
    
    video_source_changed = True
    return jsonify({"ok": True})

@app.route("/api/switch", methods=["POST"])
def api_switch():
    data = request.get_json(force=True); target = int(data.get("target", 1))
    state["control_mode"] = "manual"; state["traffic_detection_active"] = False
    if state["pause_active"]: state["pause_active"] = False
    threading.Thread(target=switch_traffic_light, args=(target,), daemon=True).start()
    return jsonify({"ok": True})

@app.route("/api/pause", methods=["POST"])
def api_pause(): state["control_mode"] = "manual"; pause_traffic_lights(); return jsonify({"ok": True})
@app.route("/api/resume", methods=["POST"])
def api_resume(): state["control_mode"] = "manual"; resume_traffic_lights(); return jsonify({"ok": True})
@app.route("/api/set_mode", methods=["POST"])
def api_set_mode():
    data = request.get_json(force=True); mode = data.get("mode")
    state["control_mode"] = mode
    state["traffic_detection_active"] = (mode == "traffic")
    state["timer_active"] = (mode == "timer")
    return jsonify({"ok": True})
@app.route("/api/set_led", methods=["POST"])
def api_set_led():
    data = request.get_json(force=True); state["control_mode"] = "manual"; cmd = data.get("cmd")
    if cmd:
        parts = cmd.split("_")
        if len(parts) == 2 and parts[0] in LED_STATE: LED_STATE[parts[0]] = (parts[1] == "on")
    update_arduino_leds(); return jsonify({"ok": True})
@app.route("/command")
def arduino_command(): return Response(" ".join(ARDUINO_COMMAND_BUFFER), mimetype='text/plain')
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True)
    q = data.get("question", "").lower()
    res = "Je n'ai pas compris votre demande."
    
    # 1. Gestion de la PAUSE
    if "pause" in q or "stop" in q:
        state["control_mode"] = "manual"
        pause_traffic_lights()
        res = "Système mis en PAUSE (Feux clignotants/Rouge)."

    # 2. Gestion de la REPRISE
    elif "reprendre" in q or "continue" in q:
        state["control_mode"] = "manual"
        resume_traffic_lights()
        res = "Reprise du fonctionnement normal."

    # 3. Changement de MODE (Trafic, Timer, Manuel)
    elif "mode" in q:
        if "trafic" in q or "ia" in q:
            state["control_mode"] = "traffic"
            state["traffic_detection_active"] = True
            state["timer_active"] = False
            res = "Mode TRAFIC IA activé."
        elif "timer" in q or "chrono" in q:
            state["control_mode"] = "timer"
            state["traffic_detection_active"] = False
            state["timer_active"] = True
            res = "Mode TIMER activé."
        elif "manuel" in q:
            state["control_mode"] = "manual"
            state["traffic_detection_active"] = False
            state["timer_active"] = False
            res = "Mode MANUEL activé."

    # 4. Commandes de SWITCH (Déjà existant)
    elif "switch" in q or "passer" in q:
        state["control_mode"] = "manual"
        if "1" in q or "un" in q:
            threading.Thread(target=switch_traffic_light, args=(1,), daemon=True).start()
            res = "Passage au Feu 1 Vert."
        elif "2" in q or "deux" in q:
            threading.Thread(target=switch_traffic_light, args=(2,), daemon=True).start()
            res = "Passage au Feu 2 Vert."

    # 5. Scénarios (Ambulance / Live)
    elif "test" in q or "ambulance" in q:
        global current_video_source, video_source_changed
        current_video_source = TEST_SCENARIO_PATH # Utilisation de la variable corrigée
        video_source_changed = True
        res = "Lancement du scénario d'urgence (Pompier)."
    elif "live" in q or "direct" in q:
        current_video_source = LIVE_SURVEILLANCE_URL
        video_source_changed = True
        res = "Retour au flux vidéo en direct."

    # 6. Fallback IA (DeepSeek)
    else:
        # Optionnel : si tu veux que l'IA réponde aux questions générales
        ai = ask_deepseek(q)
        if ai: res = ai

    return jsonify({"answer": res})
@app.route("/api/map")
def api_map():
    lights = []
    for light in MAP_CONFIG["lights"]:
        lid = light["id"]; status = "red"
        if LED_STATE.get(f"green{lid}"): status = "green"
        elif LED_STATE.get(f"yellow{lid}"): status = "yellow"
        lights.append({"id": lid, "name": light["name"], "position": light["position"], "status": status})
    return jsonify({"center": MAP_CONFIG["center"], "lights": lights})
@app.route("/api/detect_traffic_incidents", methods=["POST"])
def api_detect_traffic_incidents():
    if not GOOGLE_MAPS_API_KEY: return jsonify({"ok": False, "error": "Clé manquante"})
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {"location": f"{MAP_CONFIG['center']['lat']},{MAP_CONFIG['center']['lng']}", "radius": 5000, "keyword": "traffic", "key": GOOGLE_MAPS_API_KEY}
        resp = requests.get(url, params=params, timeout=5).json()
        found = []
        if resp.get("status") == "OK":
            for p in resp.get("results", []):
                inc = {"id": p.get("place_id"), "type": "Alert", "location": p.get("name"), "coordinates": p["geometry"]["location"], "timestamp": datetime.now().isoformat()}
                if not any(i['id']==inc['id'] for i in state["incidents"]): found.append(inc); state["incidents"].append(inc)
        return jsonify({"ok": True, "incidents": found})
    except Exception as e: return jsonify({"ok": False, "error": str(e)})
@app.route("/api/incidents", methods=["GET", "POST"])
def api_incidents():
    if request.method == "POST":
        data = request.get_json(force=True)
        if data.get("method") == "DELETE":
            state["incidents"] = [i for i in state["incidents"] if i.get("id") != data.get("id")]
            return jsonify({"ok": True})
        new_inc = {"id": random.randint(1000,9999), "type": data.get("type"), "location": f"Feu {data.get('light_id')}", "coordinates": MAP_CONFIG["center"], "timestamp": datetime.now().isoformat()}
        state["incidents"].append(new_inc)
        return jsonify({"ok": True})
    return jsonify({"incidents": state["incidents"]})
@app.route("/api/upload_video", methods=["POST"])
def api_upload():
    global current_video_source, video_source_changed
    if 'file' not in request.files: return jsonify({"ok": False})
    file = request.files['file']
    if file.filename != '':
        path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(path)
        current_video_source = path; video_source_changed = True
        return jsonify({"ok": True})
    return jsonify({"ok": False})
@app.route("/api/analytics")
def api_analytics(): return jsonify({"history": state["traffic_history"]})

def start_server():
    global yolo
    print("🚦 Démarrage...")
     # 1. On télécharge la vidéo de test AVANT de commencer
    download_test_video()
    yolo = YOLO(YOLO_MODEL_PATH)
     # On démarre sur le lien Youtube Live par défaut
    # (Ou mettez 0 ici si vous préférez démarrer sur la webcam)
    stream = extract_youtube_stream(LIVE_SURVEILLANCE_URL) 
    threading.Thread(target=yolo_loop, args=(stream,), daemon=True).start()
    threading.Thread(target=timer_loop, daemon=True).start()
    update_arduino_leds()
    app.run(host="0.0.0.0", port=5000, threaded=True)

if __name__ == "__main__":
    start_server()