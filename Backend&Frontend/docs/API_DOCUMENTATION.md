# Documentation API - Système de Feux de Circulation

## Endpoints Disponibles

### 1. Statut du Système

**GET** `/api/status`

Retourne l'état complet du système.

**Réponse:**
\`\`\`json
{
  "control_mode": "traffic",
  "leds": {
    "red1": true,
    "yellow1": false,
    "green1": false,
    "red2": false,
    "yellow2": false,
    "green2": true
  },
  "stats": {
    "cars": 12,
    "buses": 2,
    "trucks": 1,
    "motorcycles": 3,
    "pedestrians": 5
  },
  "current_traffic_light": 2,
  "incidents": [],
  "traffic_history_count": 45,
  "n8n_enabled": true
}
\`\`\`

---

### 2. Configuration de la Carte

**GET** `/api/map`

Retourne la configuration des feux et leur état pour Google Maps.

**Réponse:**
\`\`\`json
{
  "center": {"lat": 33.2585, "lng": -8.5087},
  "lights": [
    {
      "id": 1,
      "name": "Feu 1 - Av. Mohamed VI",
      "position": {"lat": 33.2587, "lng": -8.5089},
      "status": "red",
      "direction": "Nord-Sud",
      "priority": 1,
      "incidents": []
    }
  ]
}
\`\`\`

---

### 3. Gestion des Incidents

#### Lister les incidents

**GET** `/api/incidents`

**Réponse:**
\`\`\`json
{
  "incidents": [
    {
      "id": 1,
      "type": "roadwork",
      "location": "Av. Mohamed VI",
      "light_id": 1,
      "description": "Travaux de réparation",
      "severity": "high",
      "timestamp": "2025-01-15T10:30:00",
      "active": true
    }
  ]
}
\`\`\`

#### Créer un incident

**POST** `/api/incidents`

**Corps de la requête:**
\`\`\`json
{
  "type": "roadwork",
  "location": "Av. Mohamed VI",
  "light_id": 1,
  "description": "Travaux de réparation",
  "severity": "high"
}
\`\`\`

**Réponse:**
\`\`\`json
{
  "ok": true,
  "incident": {
    "id": 1,
    "type": "roadwork",
    "location": "Av. Mohamed VI",
    "light_id": 1,
    "description": "Travaux de réparation",
    "severity": "high",
    "timestamp": "2025-01-15T10:30:00",
    "active": true
  }
}
\`\`\`

**Note:** Si `severity` est "high", le système mettra automatiquement les feux en pause.

#### Supprimer un incident

**DELETE** `/api/incidents`

**Corps de la requête:**
\`\`\`json
{
  "id": 1
}
\`\`\`

**Réponse:**
\`\`\`json
{
  "ok": true
}
\`\`\`

---

### 4. Historique du Trafic

**GET** `/api/traffic-history?limit=50`

**Paramètres:**
- `limit` (optionnel): Nombre d'entrées à retourner (défaut: 50)

**Réponse:**
\`\`\`json
{
  "history": [
    {
      "timestamp": "2025-01-15T10:30:00",
      "vehicles": 15,
      "stats": {
        "cars": 12,
        "buses": 2,
        "trucks": 1,
        "motorcycles": 0,
        "pedestrians": 0
      }
    }
  ],
  "total": 100
}
\`\`\`

---

### 5. Analytics

**GET** `/api/analytics`

Retourne des statistiques analytiques.

**Réponse:**
\`\`\`json
{
  "average_vehicles": 12.5,
  "total_entries": 100,
  "peak_hours": [
    {"hour": 8, "avg_vehicles": 25.3},
    {"hour": 18, "avg_vehicles": 22.1},
    {"hour": 12, "avg_vehicles": 18.7}
  ],
  "current_stats": {
    "cars": 10,
    "buses": 1,
    "trucks": 0,
    "motorcycles": 2,
    "pedestrians": 3
  }
}
\`\`\`

---

### 6. Changer le Mode de Contrôle

**POST** `/api/set_mode`

**Corps de la requête:**
\`\`\`json
{
  "mode": "traffic"
}
\`\`\`

**Modes disponibles:**
- `manual`: Contrôle manuel
- `timer`: Timer automatique
- `traffic`: Détection de trafic
- `chatbot`: Contrôle par chatbot
- `voice`: Contrôle vocal

**Réponse:**
\`\`\`json
{
  "ok": true,
  "mode": "traffic"
}
\`\`\`

---

### 7. Switch Manuel des Feux

**POST** `/api/switch`

**Corps de la requête:**
\`\`\`json
{
  "target": 1
}
\`\`\`

**Paramètres:**
- `target`: 1 ou 2 (quel feu doit devenir vert)

**Réponse:**
\`\`\`json
{
  "ok": true,
  "switched_to": 1
}
\`\`\`

---

### 8. Pause / Reprise

#### Mettre en pause

**POST** `/api/pause`

Met tous les feux en jaune (mode pause).

**Réponse:**
\`\`\`json
{
  "ok": true,
  "paused": true
}
\`\`\`

#### Reprendre

**POST** `/api/resume`

Reprend le fonctionnement normal.

**Réponse:**
\`\`\`json
{
  "ok": true,
  "resumed": true
}
\`\`\`

---

### 9. Contrôle Manuel des LEDs

**POST** `/api/set_led`

**Corps de la requête (Option 1 - Commande):**
\`\`\`json
{
  "cmd": "green1_on"
}
\`\`\`

**Corps de la requête (Option 2 - États directs):**
\`\`\`json
{
  "leds": {
    "red1": true,
    "yellow1": false,
    "green1": false,
    "red2": false,
    "yellow2": true,
    "green2": false
  }
}
\`\`\`

**Note:** Fonctionne uniquement en mode `manual`, `voice` ou `chatbot`.

**Réponse:**
\`\`\`json
{
  "ok": true,
  "leds": {
    "red1": true,
    "yellow1": false,
    "green1": false,
    "red2": false,
    "yellow2": true,
    "green2": false
  }
}
\`\`\`

---

### 10. Chatbot

**POST** `/api/chat`

**Corps de la requête:**
\`\`\`json
{
  "question": "switch vers feu 1"
}
\`\`\`

**Commandes supportées:**
- "switch vers feu 1/2"
- "pause" / "reprendre"
- "statistiques" / "trafic"
- "incidents"
- "allumer rouge 1", etc.

**Réponse:**
\`\`\`json
{
  "answer": "Switch vers Feu Rouge 1 en cours... (Jaune 4s puis Vert)"
}
\`\`\`

---

## Webhooks N8N

Tous les événements importants sont envoyés automatiquement à N8N si configuré.

### Format des Notifications

\`\`\`json
{
  "timestamp": "2025-01-15T10:30:00",
  "event_type": "high_traffic",
  "data": {
    "vehicle_count": 25,
    "details": {"cars": 20, "buses": 3, "trucks": 2},
    "action": "automatic_switch"
  },
  "traffic_light_status": {
    "current_light": 1,
    "leds": {...},
    "control_mode": "traffic"
  }
}
\`\`\`

### Types d'Événements

- `high_traffic`: Trafic élevé détecté
- `mode_changed`: Changement de mode
- `light_switch`: Switch de feu effectué
- `incident_created`: Nouvel incident signalé
- `incident_resolved`: Incident résolu
- `traffic_paused`: Système en pause
- `traffic_resumed`: Système repris

---

## Exemples d'Utilisation

### Exemple 1: Créer un incident et recevoir une alerte

\`\`\`bash
# Créer un incident
curl -X POST http://localhost:5000/api/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "type": "accident",
    "location": "Av. Mohamed VI",
    "light_id": 1,
    "severity": "high",
    "description": "Accident de voiture bloquant la voie"
  }'

# N8N recevra automatiquement une notification
\`\`\`

### Exemple 2: Surveiller le trafic en temps réel

\`\`\`python
import requests
import time

while True:
    response = requests.get('http://localhost:5000/api/status')
    data = response.json()
    
    vehicles = sum([
        data['stats'].get('cars', 0),
        data['stats'].get('buses', 0),
        data['stats'].get('trucks', 0)
    ])
    
    print(f"Véhicules détectés: {vehicles}")
    print(f"Feu actif: {data['current_traffic_light']}")
    
    time.sleep(5)
\`\`\`

### Exemple 3: Intégration avec un système externe

\`\`\`javascript
// Webhook receiver dans N8N ou autre système
app.post('/webhook/traffic-alert', (req, res) => {
  const event = req.body;
  
  if (event.event_type === 'high_traffic') {
    // Envoyer une alerte Slack
    sendSlackAlert(`⚠️ Trafic élevé détecté: ${event.data.vehicle_count} véhicules`);
  }
  
  if (event.event_type === 'incident_created') {
    // Logger dans une base de données
    db.incidents.insert(event.data);
  }
  
  res.json({received: true});
});
\`\`\`

---

## Codes d'Erreur

- `200 OK`: Requête réussie
- `400 Bad Request`: Paramètres invalides
- `403 Forbidden`: Action non autorisée dans le mode actuel
- `500 Internal Server Error`: Erreur serveur

---

## Rate Limiting

Aucune limite de débit n'est actuellement implémentée, mais il est recommandé de ne pas faire plus de 10 requêtes par seconde pour éviter de surcharger le système.
