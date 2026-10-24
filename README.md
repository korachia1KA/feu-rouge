# 🚦 Carrefour Intelligent — Feu Rouge Intelligent (GRID CONTROL)

Système de **gestion intelligente d'un carrefour** à deux feux, combinant **vision par ordinateur (YOLOv8)**, **IoT (ESP8266)**, un **dashboard web temps réel**, un **assistant IA local (Ollama)**, le **contrôle vocal** et des **alertes automatisées (n8n → Email / SMS / WhatsApp)**.

Le système détecte les voitures, bus, camions/véhicules d'urgence et piétons depuis un flux vidéo, adapte les feux en conséquence, signale les incidents (accident, bouchon, travaux, ambulance) et pilote physiquement 6 LED (2 feux tricolores) via un module ESP8266.

---

## 📑 Sommaire

1. [Fonctionnalités](#-fonctionnalités)
2. [Architecture](#-architecture)
3. [Structure du projet](#-structure-du-projet)
4. [Prérequis](#-prérequis)
5. [Installation](#-installation)
6. [Configuration](#-configuration)
7. [Lancement](#-lancement)
8. [Modes de contrôle](#-modes-de-contrôle)
9. [Pages du dashboard](#-pages-du-dashboard)
10. [API REST](#-api-rest)
11. [Montage matériel (ESP8266)](#-montage-matériel-esp8266)
12. [Intégration n8n](#-intégration-n8n)
13. [Commandes chatbot et vocales](#-commandes-chatbot-et-vocales)
14. [Sécurité](#-sécurité)
15. [Dépannage](#-dépannage)
16. [Pistes d'amélioration](#-pistes-damélioration)
17. [Auteur](#-auteur)

---

## ✨ Fonctionnalités

- **Détection IA en temps réel** (YOLOv8n) : voitures, bus, camions, piétons, avec boîtes englobantes annotées sur le flux vidéo MJPEG.
- **5 modes de contrôle** : Manuel, Switching, Trafic IA, Timer, Chatbot.
- **Contrôle individuel des 6 LED** (rouge / jaune / vert × 2 feux).
- **Cycle automatique configurable** (durée du jaune et du vert, de 1 à 60 s).
- **Détection d'urgence** (camion/bus assimilé à une ambulance ou un camion de pompier) → création d'incident + alerte n8n.
- **Détection de bouchon** (≥ 8 voitures) → incident + alerte n8n.
- **Carte live** (Leaflet / Google Maps) avec position des feux et signalement manuel d'incidents.
- **Sources vidéo multiples** : flux YouTube live, vidéo de test locale, webcam, ou upload d'une vidéo/image.
- **Assistant conversationnel** (Ollama, modèle `llama3.2`) avec commandes en langage naturel.
- **Commande vocale** en français.
- **Flux temps réel (SSE)** : l'état des feux est poussé à toutes les pages ouvertes.
- **Historique du trafic** (100 dernières mesures) pour les analytics.

---

## 🏗 Architecture

```
┌──────────────┐   HTTP GET /command (500 ms)   ┌──────────────────────────┐
│  ESP8266     │ ◄───────────────────────────── │  Serveur Flask (Python)  │
│  6 LED       │                                │  server2.py  :5000       │
└──────────────┘                                │                          │
                                                │  ├─ Thread YOLO (vidéo)  │
┌──────────────┐   MJPEG /video_feed            │  ├─ Thread Timer         │
│  Navigateur  │ ◄───────────────────────────── │  ├─ API REST + SSE       │
│  Dashboard   │   REST /api/*  · SSE /api/stream│ └─ Templates Jinja2     │
└──────────────┘                                └───────┬─────────┬────────┘
                                                        │         │
                                         Webhook POST   │         │ HTTP
                                                        ▼         ▼
                                              ┌────────────┐  ┌──────────────┐
                                              │    n8n     │  │ Ollama       │
                                              │ Email/SMS/ │  │ (llama3.2)   │
                                              │ WhatsApp   │  │ :11434       │
                                              └────────────┘  └──────────────┘
```

**Principe de communication avec le matériel :** le serveur ne pousse rien vers l'ESP8266. C'est l'ESP8266 qui interroge `GET /command` toutes les 500 ms et reçoit une chaîne du type  
`red1_on yellow1_off green1_off red2_off yellow2_on green2_off`, qu'il applique aux broches.

---

## 📁 Structure du projet

```
carrefour-intelligent/
├── server2.py                  # Serveur Flask + YOLO + logique feux + API
├── requirements.txt            # Dépendances Python
├── Feu_Rouge_Chat_Boot.ino     # Firmware ESP8266 (Arduino IDE)
├── yolov8n.pt                  # Modèle YOLO (téléchargé automatiquement par ultralytics)
├── uploads/
│   └── test_pompier.mp4        # Vidéo de test d'urgence (à ajouter manuellement)
└── templates/
    ├── base.html               # Layout commun (rail de navigation, thème, JS partagé)
    ├── dashboard.html          # Vue d'ensemble
    ├── control.html            # Contrôle LED individuel
    ├── voice.html              # Commande vocale
    ├── automatic.html          # Configuration du timer
    ├── map.html                # Carte & signalement d'incidents
    ├── video.html              # Sources vidéo & vision IA
    ├── incidents.html          # Liste complète des incidents
    ├── analytics.html          # Analytics
    ├── n8n.html                # Statut de l'intégration n8n
    ├── chat.html               # Assistant IA
    └── index.html              # Ancienne version monopage (non utilisée par le serveur)
```

> ⚠️ Flask charge les pages depuis le dossier **`templates/`** : placez-y tous les fichiers `.html`.

---

## 🧰 Prérequis

| Composant | Détail |
|---|---|
| Python | 3.10 ou 3.11 recommandé |
| Matériel PC | CPU suffisant pour YOLOv8n ; GPU optionnel |
| Ollama | Pour l'assistant IA (`ollama pull llama3.2`) |
| n8n | Optionnel, pour les alertes Email / SMS / WhatsApp |
| ESP8266 | NodeMCU / Wemos D1 mini + 6 LED + 6 résistances |
| Arduino IDE | Avec le support carte ESP8266 |
| Clé API Google Maps | Optionnelle (Places API pour le scan d'incidents) |

---

## ⚙️ Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/korachia1KA/<nom-du-depot>.git
cd <nom-du-depot>

# 2. Environnement virtuel
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 3. Dépendances
pip install -r requirements.txt

# 4. Dossiers
mkdir -p templates uploads
```

**Dépendances (`requirements.txt`) :** `flask`, `flask-cors`, `opencv-python`, `ultralytics`, `numpy`, `yt-dlp`, `requests`, `python-dotenv`.

**Vidéo de test d'urgence :** téléchargez une vidéo de camion de pompier / ambulance, renommez-la `test_pompier.mp4` et placez-la dans `uploads/`. Sans ce fichier, le scénario « Test Urgence » ne fonctionnera pas (le serveur affiche un avertissement au démarrage).

**Assistant IA (Ollama) :**

```bash
ollama pull llama3.2
ollama serve        # écoute sur http://localhost:11434
```

---

## 🔧 Configuration

Les principaux paramètres sont en tête de `server2.py` :

| Paramètre | Valeur par défaut | Rôle |
|---|---|---|
| `LIVE_SURVEILLANCE_URL` | lien YouTube live | Source vidéo principale |
| `TEST_SCENARIO_PATH` | `uploads/test_pompier.mp4` | Scénario d'urgence |
| `FRAME_WIDTH / FRAME_HEIGHT` | `640 / 360` | Taille du flux traité |
| `PROCESS_EVERY_N_FRAMES` | `3` | Une inférence YOLO toutes les N images |
| `DETECTION_CONFIDENCE` | `0.3` | Seuil de confiance YOLO |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | Modèle de détection |
| `DEEPSEEK_API` / `DEEPSEEK_MODEL` | Ollama `:11434` / `llama3.2:latest` | Assistant IA |
| `N8N_WEBHOOK_URL` | `http://localhost:5678/webhook/traffic-alert` | Webhook n8n |
| `N8N_ENABLED` | `true` | Activer / désactiver n8n |
| `TIMER_CONFIG` | jaune 4 s / vert 5 s | Cycle du mode Timer |
| `MAP_CONFIG` | Coordonnées des 2 feux | Centre de la carte et position des feux |

**Variables d'environnement recommandées** (fichier `.env`, `python-dotenv` est déjà dans les dépendances) :

```env
GOOGLE_MAPS_API_KEY=votre_cle_ici
N8N_WEBHOOK_URL=http://localhost:5678/webhook/traffic-alert
N8N_ENABLED=true
```

Pour tester n8n avec « Listen for test event » :

```bash
# Windows
set N8N_WEBHOOK_URL=http://localhost:5678/webhook-test/traffic-alert
# Linux / macOS
export N8N_WEBHOOK_URL=http://localhost:5678/webhook-test/traffic-alert
```

---

## ▶️ Lancement

```bash
python server2.py
```

- Dashboard : **http://localhost:5000**
- Depuis un autre appareil du réseau : `http://<IP-du-PC>:5000`
- Flash de l'ESP8266 : voir [Montage matériel](#-montage-matériel-esp8266). L'IP du PC doit correspondre à celle écrite dans le firmware.

Au démarrage, le serveur : vérifie la vidéo de test → charge YOLO → extrait le flux YouTube → lance les threads **YOLO** et **Timer** → démarre Flask sur le port `5000`.

---

## 🎛 Modes de contrôle

| Mode | Comportement |
|---|---|
| **Manuel** | Aucune automatisation ; contrôle LED par LED depuis la page *Contrôle LEDs*. |
| **Switching** | Boutons directs : Feu 1 vert, Feu 2 vert, Pause, Reprise. |
| **Trafic IA** | Si plus de 10 véhicules (voitures + bus + camions) sont détectés, les feux basculent. |
| **Timer** | Alternance automatique Feu 1 / Feu 2 selon les durées configurées. |
| **Chatbot** | Pilotage par phrases en langage naturel (voir plus bas). |

**Séquence de transition :** lors d'un changement, le feu qui va passer au vert reste rouge pendant que l'autre passe au **jaune** (durée `yellow_transition`), puis le nouvel état est appliqué.

**Pause :** les deux feux passent au jaune (clignotant / attention). **Reprise :** retour à l'état normal du dernier feu vert.

---

## 🖥 Pages du dashboard

| Route | Page | Contenu |
|---|---|---|
| `/` | Dashboard | Sélecteur de mode, état des 2 feux, compteurs voitures / piétons, flux vidéo YOLO |
| `/control` | Contrôle LEDs | 6 cartes LED avec ON / OFF |
| `/voice` | Contrôle vocal | Bouton micro et liste des commandes |
| `/automatic` | Timer | Réglage durées jaune / vert (sauvegarde locale + serveur) |
| `/map` | Carte live | Feux sur la carte, scan d'incidents, signalement manuel |
| `/video` | Vidéo & IA | Choix de la source (live / urgence / upload) |
| `/incidents` | Incidents | Liste complète |
| `/analytics` | Analytics | Historique du trafic |
| `/n8n` | N8N | Statut et schéma du workflow |
| `/chat` | Assistant IA | Chat + raccourcis de commandes |

---

## 🔌 API REST

### Pilotage

| Méthode | Route | Corps JSON | Description |
|---|---|---|---|
| GET | `/api/status` | — | Mode, LED, stats, pause, feu actif, état n8n |
| GET | `/api/stream` | — | **SSE** : état des feux en temps réel |
| POST | `/api/set_mode` | `{"mode": "manual\|switching\|traffic\|timer\|chatbot"}` | Change le mode |
| POST | `/api/switch` | `{"target": 1\|2}` | Donne le vert au feu choisi |
| POST | `/api/pause` | — | Met en pause (jaune) |
| POST | `/api/resume` | — | Reprend |
| POST | `/api/set_led` | `{"cmd": "red1_on"}` | Allume / éteint une LED |
| GET / POST | `/api/timer_config` | `{"yellow": 4, "green": 5}` | Lit / modifie le timer (1–60 s) |
| GET | `/command` | — | Chaîne de commandes lue par l'ESP8266 |

### Vidéo & IA

| Méthode | Route | Description |
|---|---|---|
| GET | `/video_feed` | Flux MJPEG annoté |
| POST | `/api/set_source` | `{"type": "live\|test_ambulance\|webcam"}` |
| POST | `/api/upload_video` | Upload d'une vidéo ou image (`multipart/form-data`, champ `file`) |
| POST | `/api/chat` | `{"question": "..."}` → `{"answer": "..."}` |

### Carte, incidents, analytics

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/map` | Centre, feux et statut couleur |
| POST | `/api/detect_traffic_incidents` | Scan Google Places autour du carrefour |
| GET / POST | `/api/incidents` | Liste / création / suppression (`{"method":"DELETE","id":...}`) |
| GET | `/api/analytics` | Historique du trafic |

---

## 🔩 Montage matériel (ESP8266)

**Brochage utilisé dans `Feu_Rouge_Chat_Boot.ino` :**

| LED | Broche NodeMCU |
|---|---|
| Rouge 1 | `D0` |
| Jaune 1 | `D1` |
| Vert 1 | `D2` |
| Rouge 2 | `D5` |
| Jaune 2 | `D6` |
| Vert 2 | `D7` |

Chaque LED doit être placée en série avec une résistance (220 Ω – 330 Ω) vers la masse (GND).

**Configuration du firmware :**

1. Installer le support ESP8266 dans l'Arduino IDE (gestionnaire de cartes).
2. Modifier dans le `.ino` : le SSID, le mot de passe Wi-Fi et l'URL du serveur  
   `http://<IP-du-PC>:5000/command`.
3. Sélectionner la carte (NodeMCU 1.0) et téléverser.
4. Ouvrir le moniteur série à **115200 bauds** : on doit voir « Connecté ! » puis les commandes reçues.

> Le PC et l'ESP8266 doivent être sur le **même réseau local**.

---

## 🔔 Intégration n8n

Le serveur envoie un `POST` JSON vers le webhook `traffic-alert` **uniquement** pour deux événements :

- `ambulance_detected`
- `congestion_detected`

Les changements de feux ne déclenchent volontairement **aucune** notification.

**Exemple de payload :**

```json
{
  "timestamp": "2026-10-24T14:32:10.123456",
  "event_type": "ambulance_detected",
  "data": {
    "msg": "🚑 Véhicule d'urgence détecté ! Priorité demandée.",
    "location": "Feu 1",
    "count": { "cars": 3, "buses": 0, "trucks": 1, "motorcycles": 0, "pedestrians": 2 }
  }
}
```

**Workflow :**

```
Webhook (POST) → Switch (rules sur event_type) ─┬─ Send Email
                                                └─ Send SMS / WhatsApp
```

Un délai de **20 secondes** (cooldown) évite de spammer les alertes.

---

## 💬 Commandes chatbot et vocales

| Intention | Exemples |
|---|---|
| Pause / reprise | « Pause », « Stop », « Reprendre », « Continue » |
| Changer de mode | « Mode trafic IA », « Mode timer », « Mode manuel » |
| Changer de feu | « Switch vers feu 1 », « Passer au feu 2 » |
| Scénarios vidéo | « Test ambulance », « Retour au live » |
| LED (voix) | « Allumer rouge 1 », « Éteindre jaune 2 » |
| Question libre | Toute autre phrase est envoyée à Ollama (`llama3.2`) |

---

## 🔐 Sécurité

Avant de publier le dépôt sur GitHub :

- **Ne jamais committer** de clé API (Google Maps) ni de mot de passe Wi-Fi. Déplacez-les dans un fichier `.env` et ajoutez `.env` au `.gitignore`.
- Si une clé a déjà été publiée ou partagée, **révoquez-la et régénérez-en une** dans la console Google Cloud, puis restreignez-la (par domaine / par API).
- Le serveur écoute sur `0.0.0.0` et CORS est ouvert : acceptable en démonstration locale, mais à restreindre (authentification, CORS ciblé, `debug` désactivé) pour tout déploiement réel.

**Exemple de `.gitignore` :**

```
venv/
__pycache__/
.env
uploads/*
!uploads/.gitkeep
yolov8n.pt
```

---

## 🛠 Dépannage

| Problème | Piste de solution |
|---|---|
| Flux vidéo noir / pas d'image | Le lien YouTube peut être indisponible ou restreint : le serveur retombe sur la webcam (`0`). Mettre à jour `LIVE_SURVEILLANCE_URL` ou utiliser une vidéo locale. |
| `yt-dlp` échoue | Mettre à jour : `pip install -U yt-dlp` |
| « Test Urgence » sans effet | Vérifier que `uploads/test_pompier.mp4` existe |
| Chat IA ne répond pas | Vérifier qu'Ollama tourne et que `llama3.2` est installé |
| Alertes n8n absentes | Workflow actif ? URL `webhook` (prod) vs `webhook-test` ? `N8N_ENABLED=true` ? |
| LED ne réagissent pas | Même réseau Wi-Fi ? IP du PC correcte dans le `.ino` ? Pare-feu ouvert sur le port 5000 ? |
| Templates introuvables | Les `.html` doivent être dans `templates/` |
| Page `/analytics` affiche le contenu n8n | Voir les notes ci-dessous |

---

## 🚀 Pistes d'amélioration

- Priorité automatique aux véhicules d'urgence (passage au vert immédiat) au lieu d'une simple alerte.
- Modèle YOLO entraîné spécifiquement sur ambulances / camions de pompiers (le camion actuel est un proxy approximatif).
- Page Analytics avec vrais graphiques (Chart.js) à partir de `/api/analytics`.
- Persistance des incidents et de l'historique (SQLite / MySQL).
- Authentification sur le dashboard et l'API.
- Passage à MQTT ou WebSocket pour remplacer le polling HTTP de l'ESP8266.
- Moteur de décision plus fin (temps d'attente, file d'attente par voie, comptage par zone).
- Conteneurisation Docker (Flask + n8n + Ollama).

---

## 📝 Notes sur le code actuel

- `analytics.html` contient actuellement le gabarit de la page **N8N** (copie) : à remplacer par une vraie page d'analytics.
- `n8n.html` utilise l'ancien design system ; `analytics.html` utilise le nouveau (bento). À harmoniser.
- `index.html` est l'ancienne version monopage ; elle n'est plus servie par `server2.py`.
- Le mode « Trafic IA » est exécuté à la fois dans `yolo_loop` et via `decide_traffic_command` (non appelée) : une seule logique devrait être conservée.

---

## 👤 Auteur

**Abdelghafour Korachi** — étudiant en ingénierie télécommunications  
GitHub : [@korachia1KA](https://github.com/korachia1KA) · LinkedIn : [abdelghafour-korachi](https://www.linkedin.com/in/abdelghafour-korachi-0a33773a8/)

---

## 📄 Licence

Projet académique — licence à définir (MIT recommandée si vous souhaitez le partager).
