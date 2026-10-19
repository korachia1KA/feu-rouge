# Installation du Système de Feux de Circulation Intelligents

## Prérequis

- Python 3.8 ou supérieur
- Compte Google Cloud Platform (pour Google Maps API)
- Instance N8N (optionnel mais recommandé)
- Webcam ou flux vidéo YouTube

## Installation

### 1. Cloner le projet

\`\`\`bash
git clone <votre-repo>
cd traffic-light-system
\`\`\`

### 2. Installer les dépendances Python

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 3. Configuration des variables d'environnement

Copiez le fichier `.env.example` en `.env` et configurez vos clés API:

\`\`\`bash
cp .env.example .env
\`\`\`

Éditez `.env` avec vos valeurs:
- `YOUTUBE_URL`: URL de votre flux vidéo
- `N8N_WEBHOOK_URL`: URL du webhook N8N
- `GOOGLE_MAPS_API_KEY`: Votre clé API Google Maps

### 4. Télécharger le modèle YOLO

Le modèle YOLOv8n sera téléchargé automatiquement au premier lancement.

### 5. Lancer l'application

\`\`\`bash
python app.py
\`\`\`

L'application sera accessible sur `http://localhost:5000`

## Configuration N8N

### Installation de N8N

\`\`\`bash
npm install -g n8n
n8n start
\`\`\`

N8N sera accessible sur `http://localhost:5678`

### Créer le Workflow

1. Ouvrez N8N dans votre navigateur
2. Créez un nouveau workflow
3. Ajoutez un nœud **Webhook** avec le path `/traffic-alert`
4. Ajoutez les nœuds de traitement (Slack, Email, Database, etc.)
5. Consultez `N8N_WORKFLOWS.md` pour des exemples complets

## Configuration Google Maps

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet
3. Activez l'API Maps JavaScript
4. Créez une clé API
5. Ajoutez la clé dans `.env`

## Utilisation

### Modes de Contrôle

- **Manuel**: Contrôle direct des LEDs
- **Timer**: Alternance automatique programmée
- **Trafic**: Détection intelligente avec YOLO
- **Chatbot**: Contrôle par commandes textuelles
- **Vocal**: Contrôle par reconnaissance vocale

### Gestion des Incidents

1. Accédez à l'onglet "Incidents"
2. Remplissez le formulaire
3. Le système s'adaptera automatiquement
4. N8N recevra une notification

### Analytics

Consultez l'onglet "Analytics" pour:
- Historique du trafic
- Véhicules moyens par détection
- Heures de pointe
- Statistiques détaillées

## Dépannage

### Le flux vidéo ne fonctionne pas

- Vérifiez que l'URL YouTube est correcte
- Assurez-vous que yt-dlp est à jour: `pip install -U yt-dlp`

### N8N ne reçoit pas les notifications

- Vérifiez que `N8N_ENABLED=true` dans `.env`
- Vérifiez l'URL du webhook
- Testez avec curl: `curl -X POST http://localhost:5678/webhook/traffic-alert -H "Content-Type: application/json" -d '{"test": true}'`

### YOLO ne détecte rien

- Vérifiez l'éclairage de la vidéo
- Ajustez `DETECTION_CONFIDENCE` (plus bas = plus sensible)
- Essayez un autre modèle YOLO (yolov8s.pt, yolov8m.pt)

## Support

Pour toute question, ouvrez une issue sur GitHub ou consultez la documentation N8N.
