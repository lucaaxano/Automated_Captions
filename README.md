# Subtitle Microservice

API-basierter Service für Forced Alignment und Subtitle Rendering. Perfekt für automatisierte Video-Pipelines (n8n, Make, etc.).

## Features

- **Forced Alignment**: Exakte Timecodes aus Script + Audio (kein ASR, keine Fehler)
- **ASS Rendering**: Moderne TikTok-Style Untertitel
- **API-First**: Einfache HTTP Integration
- **Docker Ready**: Ein Befehl zum Deployen

## Quick Start

### Mit Docker (empfohlen)

```bash
# Repository klonen
git clone <repo-url>
cd Automated_Captions

# Environment konfigurieren
cp .env.example .env
# API_KEY in .env setzen!

# Starten
docker-compose up -d --build
```

Der Service läuft dann unter `http://localhost:8000`.

### Lokal (Entwicklung)

```bash
# Voraussetzungen: Python 3.10+, FFmpeg, espeak-ng

# Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Environment
cp .env.example .env

# Starten
uvicorn app.main:app --reload
```

## API Endpoints

### POST /align

Forced Alignment von Script zu Audio.

**Request:**
```bash
curl -X POST http://localhost:8000/align \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "script_text": "Xin chào. Đây là một ví dụ.",
    "language": "vie"
  }'
```

**Response:**
```json
{
  "segments": [
    {"start": 0.42, "end": 2.31, "text": "Xin chào."},
    {"start": 2.35, "end": 4.80, "text": "Đây là một ví dụ."}
  ],
  "duration": 5.0,
  "language": "vie"
}
```

### POST /render

Video mit Untertiteln rendern.

**Request:**
```bash
curl -X POST http://localhost:8000/render \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "segments": [
      {"start": 0.42, "end": 2.31, "text": "Xin chào."},
      {"start": 2.35, "end": 4.80, "text": "Đây là một ví dụ."}
    ],
    "style_preset": "tiktok_clean"
  }' \
  --output subtitled_video.mp4
```

### GET /styles

Verfügbare Style Presets auflisten.

```bash
curl http://localhost:8000/styles \
  -H "X-API-Key: your-api-key"
```

### GET /health

Health Check (keine Auth erforderlich).

```bash
curl http://localhost:8000/health
```

## n8n Integration

### Workflow: Align + Render

1. **HTTP Request Node (Align)**:
   - Method: POST
   - URL: `http://<server>:8000/align`
   - Headers: `X-API-Key: {{$env.SUBTITLE_API_KEY}}`
   - Body (JSON):
     ```json
     {
       "video_url": "{{$json.video_url}}",
       "script_text": "{{$json.script}}",
       "language": "vie"
     }
     ```

2. **HTTP Request Node (Render)**:
   - Method: POST
   - URL: `http://<server>:8000/render`
   - Headers: `X-API-Key: {{$env.SUBTITLE_API_KEY}}`
   - Body (JSON):
     ```json
     {
       "video_url": "{{$json.video_url}}",
       "segments": "{{$json.segments}}",
       "style_preset": "tiktok_clean"
     }
     ```
   - Response Format: File

## Style Presets

| Preset | Beschreibung |
|--------|--------------|
| `tiktok_clean` | Standard TikTok-Style, weiß mit schwarzem Outline |
| `tiktok_bold` | Größere, fettere Schrift |
| `minimal` | Minimalistisch, ohne Shadow |

## Deployment auf Hetzner VPS

### 1. Server Setup

```bash
# Ubuntu 22.04 LTS
apt update && apt upgrade -y

# Docker installieren
curl -fsSL https://get.docker.com | sh

# Docker Compose installieren
apt install docker-compose-plugin
```

### 2. Projekt deployen

```bash
# Repository klonen
git clone <repo-url> /opt/subtitle-service
cd /opt/subtitle-service

# Environment konfigurieren
cp .env.example .env
nano .env  # API_KEY setzen!

# Starten
docker compose up -d --build
```

### 3. Optional: HTTPS mit Caddy

```bash
# Caddyfile erstellen
cat > /etc/caddy/Caddyfile << EOF
subtitle-api.deinedomain.de {
    reverse_proxy localhost:8000
}
EOF

# Caddy installieren und starten
apt install caddy
systemctl enable caddy
systemctl start caddy
```

## Unterstützte Sprachen

| Code | Sprache |
|------|---------|
| `vie` | Vietnamesisch |
| `deu` | Deutsch |
| `eng` | Englisch |
| `fra` | Französisch |
| `spa` | Spanisch |
| `ita` | Italienisch |
| `por` | Portugiesisch |
| `rus` | Russisch |
| `zho` | Chinesisch |
| `jpn` | Japanisch |
| `kor` | Koreanisch |

## Entwicklung

### Tests ausführen

```bash
pytest tests/ -v
```

### Projektstruktur

```
Automated_Captions/
├── app/
│   ├── main.py           # FastAPI Entry
│   ├── config.py         # Settings
│   ├── auth.py           # API Key Auth
│   ├── routers/
│   │   ├── align.py      # /align Endpoint
│   │   └── render.py     # /render Endpoint
│   ├── services/
│   │   ├── alignment.py  # Forced Alignment
│   │   ├── ass_generator.py
│   │   ├── video.py
│   │   └── ffmpeg.py
│   ├── models/
│   │   └── schemas.py    # Pydantic Models
│   └── templates/
│       └── styles.py     # ASS Styles
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Troubleshooting

### "Aeneas not installed"
Aeneas benötigt espeak-ng. Im Docker-Image ist alles enthalten. Lokal:
```bash
apt install espeak-ng libespeak-ng1
pip install aeneas
```

### "FFmpeg not found"
```bash
apt install ffmpeg
```

### Video zu lang
Standard-Limit: 60 Sekunden. Ändern in `.env`:
```
MAX_VIDEO_DURATION=120
```

## Lizenz

MIT
