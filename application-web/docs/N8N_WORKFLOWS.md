# 🔗 Guide d'Intégration N8N

## Configuration N8N

### 1. Variables d'environnement

\`\`\`bash
# Activer N8N
export N8N_ENABLED=true
export N8N_WEBHOOK_URL=http://localhost:5678/webhook/traffic-alert
\`\`\`

### 2. Workflow N8N de Base

\`\`\`json
{
  "name": "Traffic Light Automation",
  "nodes": [
    {
      "parameters": {
        "path": "traffic-alert",
        "responseMode": "onReceived",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"event_type\"]}}",
              "value2": "high_traffic"
            }
          ]
        }
      },
      "name": "Is High Traffic?",
      "type": "n8n-nodes-base.if",
      "position": [450, 300]
    },
    {
      "parameters": {
        "channel": "#traffic-alerts",
        "text": "🚨 Trafic élevé détecté!\n\nNombre de véhicules: {{$json[\"data\"][\"vehicle_count\"]}}\nAction: {{$json[\"data\"][\"action\"]}}\nHeure: {{$json[\"timestamp\"]}}"
      },
      "name": "Send to Slack",
      "type": "n8n-nodes-base.slack",
      "position": [650, 200]
    },
    {
      "parameters": {
        "fromEmail": "alerts@traffic-system.com",
        "toEmail": "admin@example.com",
        "subject": "Alert: High Traffic Detected",
        "text": "High traffic detected on intersection.\n\nVehicles: {{$json[\"data\"][\"vehicle_count\"]}}"
      },
      "name": "Send Email",
      "type": "n8n-nodes-base.emailSend",
      "position": [650, 400]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Is High Traffic?", "type": "main", "index": 0}]]
    },
    "Is High Traffic?": {
      "main": [
        [
          {"node": "Send to Slack", "type": "main", "index": 0},
          {"node": "Send Email", "type": "main", "index": 0}
        ]
      ]
    }
  }
}
\`\`\`

## Types d'Événements

### 1. **high_traffic**
Déclenché quand >10 véhicules sont détectés
\`\`\`json
{
  "event_type": "high_traffic",
  "data": {
    "vehicle_count": 15,
    "details": {"cars": 12, "buses": 2, "trucks": 1},
    "action": "automatic_switch"
  }
}
\`\`\`

### 2. **incident_created**
Nouvel incident créé
\`\`\`json
{
  "event_type": "incident_created",
  "data": {
    "type": "roadwork",
    "location": "Av. Mohamed VI",
    "severity": "high"
  }
}
\`\`\`

### 3. **mode_changed**
Changement de mode de contrôle
\`\`\`json
{
  "event_type": "mode_changed",
  "data": {
    "old_mode": "manual",
    "new_mode": "traffic"
  }
}
\`\`\`

## Cas d'Usage

### 1. **Notification Slack pour Incidents**
- Webhook → Filter (incident_created) → Slack
- Message formaté avec détails de l'incident

### 2. **Email d'Alerte Trafic Élevé**
- Webhook → Filter (high_traffic) → Email
- Envoi immédiat aux responsables

### 3. **Base de Données Analytics**
- Webhook → Transform Data → PostgreSQL/MySQL
- Enregistrement de toutes les statistiques

### 4. **Intégration IoT**
- Webhook → HTTP Request → Arduino/ESP32
- Contrôle physique des feux via N8N

### 5. **Dashboard Externe**
- Webhook → Transform → Webhook externe
- Synchronisation avec système externe

## Configuration Avancée

### Filtres par Type d'Événement
\`\`\`javascript
// Dans un node Function
if (items[0].json.event_type === 'high_traffic' && 
    items[0].json.data.vehicle_count > 20) {
  return items; // Alerte critique
}
return [];
\`\`\`

### Agrégation de Données
\`\`\`javascript
// Calculer moyenne horaire
const history = items.map(i => i.json.data.vehicle_count);
const average = history.reduce((a, b) => a + b, 0) / history.length;
return [{json: {average_vehicles: average}}];
\`\`\`

### Webhook Sécurisé
\`\`\`bash
# Ajouter un token dans l'URL
export N8N_WEBHOOK_URL=http://localhost:5678/webhook/traffic-alert?token=YOUR_SECRET_TOKEN
\`\`\`

## Test du Webhook

\`\`\`bash
# Test manuel
curl -X POST http://localhost:5678/webhook/traffic-alert \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test",
    "timestamp": "2025-01-01T12:00:00",
    "data": {"message": "Test notification"}
  }'
\`\`\`

## Monitoring

Consultez les logs N8N pour voir les événements reçus:
\`\`\`bash
docker logs n8n -f
\`\`\`

## Déploiement Production

1. Utilisez HTTPS pour les webhooks
2. Ajoutez une authentification (API key, OAuth)
3. Configurez les retry policies
4. Activez la queue pour les événements critiques
5. Surveillez les métriques N8N
