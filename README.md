# ⚡ Silicon Verdict: Autonomous YouTube Production Pipeline

Pipeline 100% autónomo y contenerizado para el canal **Silicon Verdict** (Hardware de PC, arquitectura de semiconductores y telemetría de rendimiento). Genera guiones modulares en inglés técnico nativo, gráficos de benchmarks estilo Obsidian Black / Neon Cyan, montaje en FFmpeg (1080p y Shorts 9:16) y subida desatendida mediante **YouTube Data API v3** en servidores VPS Ubuntu.

---

## ⚡ Despliegue Rápido en VPS (4 Comandos)

En tu servidor VPS Ubuntu:

```bash
# 1. Clonar el repositorio y acceder
git clone https://github.com/tu-usuario/yt-automation.git /opt/yt-automation && cd /opt/yt-automation

# 2. Configurar variables de entorno (claves de Gemini, ElevenLabs y Pexels)
cp .env.example .env && nano .env

# 3. Subir el token OAuth 2.0 generado previamente desde tu PC local
scp token.json root@TU_VPS_IP:/opt/yt-automation/token.json

# 4. Aprovisionar el servidor (instala Docker + Cron) y arrancar el pipeline
sudo bash scripts/setup_server.sh && docker compose run --rm yt-runner
```

---

## 🔑 Autenticación con YouTube Data API v3 (Paso Único Local)

Antes de desplegar en el servidor VPS, ejecuta la autorización interactiva en tu máquina local:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/) > Crea un proyecto > Habilita **YouTube Data API v3**.
2. Ve a **APIs & Services > Credentials** > Crea credenciales **OAuth 2.0 Client ID** de tipo **Desktop App**.
3. Descarga el archivo JSON y guárdalo en la raíz del proyecto como `client_secrets.json`.
4. Ejecuta el script de autenticación local:
   ```bash
   pip install -r requirements.txt
   python scripts/authenticate_yt.py
   ```
5. El navegador se abrirá en `http://localhost:8080` solicitando el consentimiento del canal Silicon Verdict.
6. El script serializará el `token.json` con acceso `offline` y `refresh_token` duradero.

### 🧪 Verificación y Pruebas Offline

```bash
# 1. Test Visual Offline (Apple Liquid Glass): Renderiza frame y vídeo 1080p60 sin consumir APIs
python scripts/test_render_clip.py

# 2. Test de Subida Privada a YouTube: Valida credenciales con clip sintético
python scripts/test_upload.py

# 3. Test de Diagnóstico de Credenciales: Valida Gemini, Pixabay, ElevenLabs y YouTube
python scripts/verify_credentials.py
```

---

## 🏗️ Estructura del Proyecto

```text
yt-automation/
├── core/
│   ├── schemas.py          # Modelos Pydantic v2 (ChartData, Scene, ShortMetadata, VideoProject)
│   ├── topic_engine.py     # Descubrimiento de mercado autónomo sin duplicados (Gemini 2.0 Flash)
│   └── generator.py        # Generación de guion técnico en inglés y metadatos Silicon Verdict
├── engine/
│   ├── charts.py           # Renderizado de gráficos de benchmarks con Matplotlib (16:9 y 9:16)
│   └── renderer.py         # Ensamble FFmpeg (vídeo 1080p, gráficos intercalados y Shorts 9:16)
├── services/
│   ├── tts.py              # Síntesis neural escena por escena (ElevenLabs API)
│   ├── media.py            # Búsqueda y descarga de B-roll macro en HD (Pexels API)
│   ├── youtube.py          # Clase YouTubeService con auto-refresh y subida resumable
│   └── notifier.py         # Difusión de métricas y prompts a Discord Webhook y Telegram
├── config/
│   └── settings.py         # Configuración centralizada vía Pydantic Settings
├── scripts/
│   ├── authenticate_yt.py  # Script interactivo OAuth 2.0 (client_secrets.json -> token.json)
│   ├── test_upload.py      # Verificador sintético de subida privada a YouTube
│   └── setup_server.sh     # Aprovisionamiento para Ubuntu VPS (Docker + Docker Compose + Cron)
├── Dockerfile              # Imagen Python 3.11-slim + FFmpeg + fuentes TrueType
├── docker-compose.yml      # Definición de contenedor con volúmenes persistentes
├── history.json            # Registro persistente de temas producidos
├── topics.txt              # Cola FIFO de temas para producción desatendida
├── token.json              # Token OAuth persistente con refresh_token
├── requirements.txt
├── .env.example
└── main.py                 # Orquestador del pipeline end-to-end
```

---

## ⚙️ Modos de Ejecución

```bash
# Modo 100% Autónomo: Descubre tema de hardware, genera benchmarks y sube a YouTube
docker compose run --rm yt-runner

# Modo Tema Específico: Forzar un análisis concreto
docker compose run --rm yt-runner --topic "Why PCIe 5.0 GPUs Are a Waste of Money in 2026"

# Modo Dry-Run: Renderiza vídeo, gráficos y Shorts en local sin subir a YouTube
docker compose run --rm yt-runner --dry-run
```
