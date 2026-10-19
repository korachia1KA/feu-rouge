"""
server.py
Système central : YOLOv8 (YouTube stream) → DeepSeek → Flask API → ESP8266 LEDs
Fonctions :
 - extraction du flux YouTube via yt_dlp
 - détection en continu (ultralytics YOLO)
 - résumé JSON du trafic
 - appel DeepSeek local (http://localhost:11434/api/generate)
 - endpoints Flask:
    - GET /command        -> {"cmd": "<last_command>"}
    - POST /api/set_led   -> {"cmd": "red_on"}  (manual override)
    - GET  /api/status    -> {"cmd": ..., "stats": {...}}
    - GET  /video_feed    -> multipart/x-mixed-replace (MJPEG)
 - voice_listener thread: microphone -> text (SpeechRecognition) -> DeepSeek -> command
 - simple TTS feedback via pyttsx3
"""

import threading
import time
import json
import io
import queue
import traceback

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import requests
import cv2
from ultralytics import YOLO
import numpy as np

# For getting YouTube stream URL
import yt_dlp

# Speech and TTS
import speech_recognition as sr
import pyttsx3

# -------------- Configuration --------------
YOUTUBE_URL = "https://www.youtube.com/watch?v=_ulGbdRDyXE&t=1s"  # <-- provided
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
PROCESS_EVERY_N_FRAMES = 3  # reduce CPU by skipping frames
DEESEEK_API = "http://localhost:11434/api/generate"
DEESEEK_MODEL = "deepseek-r1:1.5b"
DETECTION_CONFIDENCE = 0.3
YOLO_MODEL_PATH = "yolov8n.pt"  # make sure this file exists or YOLO will download default
ESP_POLL_SECONDS = 1

# rules for decision (tunable)
RULES = {
    "red_on": lambda stats: (stats.get("cars", 0) + stats.get("buses", 0) + stats.get("trucks", 0)) > 10,
    "yellow_on": lambda stats: stats.get("pedestrians", 0) > 2,
    "green_on": lambda stats: (stats.get("cars", 0) + stats.get("buses", 0) + stats.get("trucks", 0)) <= 10 and stats.get("pedestrians", 0) <= 2
}

# -------------------------------------------

app = Flask(__name__)
CORS(app)

# Shared state
state = {
    "mode": "auto",  # auto or manual
    "last_command": "none",
    "last_stats": {},
    "last_ai_response": None,
    "last_frame": None,  # BGR numpy array
    "running": True
}

# Thread-safe queue for MJPEG frames
frame_queue = queue.Queue(maxsize=1)

# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 170)

# Load YOLO model
print("Loading YOLO model...")
yolo = YOLO(YOLO_MODEL_PATH)  # will download if not present
print("YOLO loaded.")


# -------------------- Utilities --------------------
def extract_youtube_stream(youtube_url):
    """
    Use yt_dlp to extract the best progressive (http) stream URL (mp4-like).
    If no progressive URL is available, try the best "format" url.
    """
    ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            # Try to find a progressive format (has 'http' and 'mp4' or 'mjpeg')
            formats = info.get("formats", [])
            # Prefer formats with 'protocol' http(s) and ext mp4 or mp4a
            candidates = []
            for f in formats:
                if f.get("protocol", "").startswith("http"):
                    # progressive stream often has 'vcodec' not 'none'
                    candidates.append(f)
            # sort by resolution descending
            candidates.sort(key=lambda x: (x.get("width") or 0, x.get("height") or 0), reverse=True)
            if candidates:
                url = candidates[0].get("url")
                return url
            # fallback to best url
            return info.get("url")
    except Exception as e:
        print("yt_dlp extraction failed:", e)
        return None


def ask_deepseek(prompt, timeout=30):
    """
    Call local DeepSeek/Ollama API. Returns the raw response text or None.
    """
    try:
        payload = {"model": DEESEEK_MODEL, "prompt": prompt, "stream": False}
        r = requests.post(DEESEEK_API, json=payload, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        # try common field names
        if isinstance(j, dict):
            if "response" in j:
                return j["response"]
            if "text" in j:
                return j["text"]
            # fallback: entire json as string
            return json.dumps(j)
        return str(j)
    except Exception as e:
        print("DeepSeek call failed:", e)
        return None


def decide_command_from_stats(stats):
    """
    Apply deterministic rules first. If none match, ask DeepSeek for a decision.
    """
    # deterministic rules
    for cmd, fn in RULES.items():
        try:
            if fn(stats):
                return cmd
        except Exception:
            pass

    # no rule matched: ask DeepSeek with a short prompt
    prompt = f"""
    Tu es un contrôleur de trafic. Résumé du trafic: {json.dumps(stats)}.
    Donne une seule commande parmi: red_on, yellow_on, green_on.
    Répond seulement par le nom de la commande.
    """
    ai = ask_deepseek(prompt)
    state["last_ai_response"] = ai
    if not ai:
        return "none"
    ai = ai.lower()
    if "red" in ai:
        return "red_on"
    if "yellow" in ai or "jaune" in ai:
        return "yellow_on"
    if "green" in ai or "vert" in ai:
        return "green_on"
    return "none"


def tts_speak(text):
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print("TTS failed:", e)


# ------------------ YOLO thread & MJPEG ------------------
def yolo_loop(stream_source=None):
    """
    Capture frames from stream_source (URL or device index).
    Perform detection every N frames, update state['last_stats'] and state['last_command'].
    Put encoded JPEG frames into frame_queue for MJPEG streaming.
    """
    global state
    if stream_source is None:
        # fallback to webcam
        stream_source = 0

    cap = cv2.VideoCapture(stream_source)
    if not cap.isOpened():
        print("Failed to open stream:", stream_source)
        return

    frame_idx = 0
    while state["running"]:
        ret, frame = cap.read()
        if not ret:
            print("Frame read failed, restarting capture in 1s...")
            time.sleep(1)
            cap.release()
            cap = cv2.VideoCapture(stream_source)
            time.sleep(1)
            continue

        # resize for performance
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        state["last_frame"] = frame.copy()

        # Put frame into MJPEG queue (non-blocking)
        try:
            _, jpeg = cv2.imencode('.jpg', frame)
            buf = jpeg.tobytes()
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except Exception:
                    pass
            frame_queue.put(buf)
        except Exception:
            pass

        # Process only every N frames
        if frame_idx % PROCESS_EVERY_N_FRAMES == 0:
            try:
                results = yolo(frame, verbose=False, conf=DETECTION_CONFIDENCE)[0]
                counts = {"cars": 0, "buses": 0, "trucks": 0, "motorcycles": 0, "pedestrians": 0}
                for box in results.boxes:
                    cls = int(box.cls)
                    name = yolo.names.get(cls, str(cls))
                    if name in ("car", "cars"):
                        counts["cars"] += 1
                    elif name in ("bus",):
                        counts["buses"] += 1
                    elif name in ("truck", "lorry"):
                        counts["trucks"] += 1
                    elif name in ("motorcycle", "motorbike"):
                        counts["motorcycles"] += 1
                    elif name in ("person", "people"):
                        counts["pedestrians"] += 1

                state["last_stats"] = counts

                # if mode is auto: decide command
                if state["mode"] == "auto":
                    cmd = decide_command_from_stats(counts)
                    if cmd != state["last_command"]:
                        print("Command changed:", cmd, "| stats:", counts)
                        state["last_command"] = cmd
                # else mode manual (UI or chat will set last_command)

            except Exception as e:
                print("YOLO processing error:", e)
                traceback.print_exc()

        frame_idx += 1
        time.sleep(0.03)  # throttle loop slightly

    cap.release()


def mjpeg_generator():
    """Yield multipart MJPEG frames from frame_queue"""
    boundary = "--frame"
    while state["running"]:
        try:
            buf = frame_queue.get(timeout=2)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buf + b'\r\n')
        except Exception:
            # if no frames, send a blank image
            blank = (255 * (np.ones((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype='uint8')))
            _, jpeg = cv2.imencode('.jpg', blank)
            b = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + b + b'\r\n')


# ------------------ Voice listener thread ------------------
# ------------------ Voice listener thread ------------------
def voice_listener_loop():
    """Écoute en continu le micro et contrôle les LED via phrases naturelles."""
    recognizer = sr.Recognizer()
    mic = None
    try:
        mic = sr.Microphone()
    except Exception as e:
        print("Microphone not available:", e)
        return

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while state["running"]:
        try:
            with mic as source:
                print("🎤 Listening for voice command...")
                audio = recognizer.listen(source, phrase_time_limit=6)
                print("🔊 Recognizing...")
                text = recognizer.recognize_google(audio, language="fr-FR").lower()
                print("🗣 You said:", text)

                cmd = None

                # -------------------- Mapping phrases to commands --------------------
                if "rouge 1" in text:
                    if "allumer" in text:
                        cmd = "red1_on"
                    elif "éteindre" in text:
                        cmd = "red1_off"
                elif "rouge 2" in text:
                    if "allumer" in text:
                        cmd = "red2_on"
                    elif "éteindre" in text:
                        cmd = "red2_off"
                elif "jaune 1" in text:
                    if "allumer" in text:
                        cmd = "yellow1_on"
                    elif "éteindre" in text:
                        cmd = "yellow1_off"
                elif "jaune 2" in text:
                    if "allumer" in text:
                        cmd = "yellow2_on"
                    elif "éteindre" in text:
                        cmd = "yellow2_off"
                elif "verte 1" in text:
                    if "allumer" in text:
                        cmd = "green1_on"
                    elif "éteindre" in text:
                        cmd = "green1_off"
                elif "verte 2" in text:
                    if "allumer" in text:
                        cmd = "green2_on"
                    elif "éteindre" in text:
                        cmd = "green2_off"

                # -------------------- Mise à jour de la commande --------------------
                if cmd:
                    print("DEBUG - commande vocale détectée:", cmd)
                    state["last_command"] = cmd
                    tts_engine.say(f"Commande reçue : {cmd.replace('_', ' ')}")
                    tts_engine.runAndWait()
                else:
                    tts_engine.say("Commande non reconnue")
                    tts_engine.runAndWait()

                time.sleep(0.5)

        except sr.UnknownValueError:
            print("Voice: nothing understood.")
        except Exception as e:
            print("Voice listener error:", e)
            time.sleep(1)



# ------------------ Flask endpoints ------------------
@app.route("/command", methods=["GET"])
def get_command():
    """Endpoint polled by ESP8266"""
    return jsonify({"cmd": state["last_command"]})


@app.route("/api/set_led", methods=["POST"])
def api_set_led():
    """
    Manual control: JSON {"cmd": "red_on"} or {"cmd":"none"} and optional {"mode":"manual" or "auto"}.
    """
    try:
        data = request.get_json(force=True)
        cmd = data.get("cmd")
        mode = data.get("mode")
        if mode in ("manual", "auto"):
            state["mode"] = mode
        if cmd:
            state["last_command"] = cmd
        return jsonify({"ok": True, "cmd": state["last_command"], "mode": state["mode"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "cmd": state["last_command"],
        "stats": state["last_stats"],
        "mode": state["mode"],
        "ai": state["last_ai_response"]
    })


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_generator(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ------------------ Start everything ------------------
def start_all(youtube_url):
    # 1) try to extract a direct stream URL
    print("Extracting stream url from YouTube...")
    stream_url = extract_youtube_stream(youtube_url)
    if not stream_url:
        print("Failed to extract YouTube stream. Falling back to webcam (0).")
        stream_url = 0

    # 2) start YOLO thread
    t_yolo = threading.Thread(target=yolo_loop, args=(stream_url,), daemon=True)
    t_yolo.start()

    # 3) voice listener
    t_voice = threading.Thread(target=voice_listener_loop, daemon=True)
    t_voice.start()


    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # seulement les erreurs seront affichées

    # 4) start flask server in main thread
    app.run(host="0.0.0.0", port=5000, threaded=True)


if __name__ == "__main__":
    try:
        state["mode"] = "manual"  # <-- désactive le mode auto
        start_all(YOUTUBE_URL)
    except KeyboardInterrupt:
        print("Shutting down...")
        state["running"] = False

