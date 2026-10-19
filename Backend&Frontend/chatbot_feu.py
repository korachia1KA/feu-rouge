from flask import Flask, jsonify
from werkzeug.serving import make_server
import requests
import logging
import os

logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask').setLevel(logging.ERROR)
logging.disable(logging.CRITICAL)

app = Flask(__name__)
app.logger.disabled = True

last_command = "none"

def ask_deepseek(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:1.5b",
                "prompt": prompt,
                "stream": False
            },
            timeout=10
        )
        data = response.json()
        return data["response"]
    except Exception as e:
        print(f"⚠️  Erreur DeepSeek: {e}")
        return None

def parse_command(text):
    text = text.lower()
    if "rouge" in text and "1" in text:
        if "allume" in text or "allumer" in text or "on" in text:
            return "red1_on"
        if "éteins" in text or "eteindre" in text or "off" in text:
            return "red1_off"
    if "rouge" in text and "2" in text:
        if "allume" in text or "allumer" in text or "on" in text:
            return "red2_on"
        if "éteins" in text or "eteindre" in text or "off" in text:
            return "red2_off"
    if "verte" in text and "1" in text:
        if "allume" in text or "allumer" in text or "on" in text:
            return "green1_on"
        if "éteins" in text or "eteindre" in text or "off" in text:
            return "green1_off"
    if "verte" in text and "2" in text:
        if "allume" in text or "allumer" in text or "on" in text:
            return "green2_on"
        if "éteins" in text or "eteindre" in text or "off" in text:
            return "green2_off"
    if "jaune" in text and "1" in text:
        if "allume" in text or "allumer" in text or "on" in text:
            return "yellow1_on"
        if "éteins" in text or "eteindre" in text or "off" in text:
            return "yellow1_off"
    if "jaune" in text and "2" in text:
        if "allume" in text or "allumer" in text or "on" in text:
            return "yellow2_on"
        if "éteins" in text or "eteindre" in text or "off" in text:
            return "yellow2_off"
    return "none"

@app.route("/command", methods=["GET"])
def get_command():
    return jsonify({"cmd": last_command})

if __name__ == "__main__":
    import threading

    def run_server():
        server = make_server("0.0.0.0", 5000, app, threaded=True)
        server.serve_forever()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("\n" + "="*50)
    print("🔴 === Chatbot LED — Commandez vos LEDs ===")
    print("="*50 + "\n")
    print("Commandes rapides:")
    print("  • 'Allumer Led rouge 1'")
    print("  • 'Éteindre Led rouge 1'")
    print("  • 'Allumer Led verte 2'")
    print("  • 'Allumer Led jaune 1'")
    print("  • Ou tapez votre commande naturelle (DeepSeek)\n")
    print("-"*50 + "\n")

    while True:
        try:
            user_input = input("→ ").strip()
            
            if not user_input:
                continue

            command = parse_command(user_input)
            
            if command != "none":
                print(f"✓ Commande détectée: {command}")
                last_command = command
            else:
                print("🤖 Analyse avec DeepSeek...")
                ai_response = ask_deepseek(user_input)
                
                if ai_response:
                    print(f"📝 DeepSeek dit: {ai_response[:100]}...")
                    command = parse_command(ai_response)
                    last_command = command
                    print(f"✓ Commande envoyée: {command}")
                else:
                    print("❌ Erreur: impossible de parser la commande")
                    last_command = "none"
            
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 Au revoir!")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}\n")
