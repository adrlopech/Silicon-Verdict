# Silicon Verdict

> Pipeline automatizado end-to-end para la generación, renderizado y publicación multicanal de microcontenido técnico y divulgativo sobre arquitectura de hardware y ciencias de la computación.

---

## 🌐 Enlaces Oficiales y Redirecciones

| Recurso | Enlace / Identificador |
| :--- | :--- |
| **Portal Web Oficial** | [adrlopech.github.io/Silicon-Verdict](https://adrlopech.github.io/Silicon-Verdict/) |
| **Términos del Servicio** | [Terms of Service](https://adrlopech.github.io/Silicon-Verdict/terms.html) |
| **Política de Privacidad** | [Privacy Policy](https://adrlopech.github.io/Silicon-Verdict/privacy.html) |
| **Canal Oficial de YouTube** | [@SiliconVerdictHQ](https://www.youtube.com/@SiliconVerdictHQ) |
| **Cuenta Oficial de TikTok** | [@siliconverdict](https://www.tiktok.com/@siliconverdict) |

---

## 📌 Visión General

**Silicon Verdict** es un framework de automatización audiovisual desarrollado en Python. Su objetivo es convertir especificaciones y análisis técnicos complejos (microarquitectura de CPUs/GPUs, jerarquías de memoria caché, buses PCIe, cuellos de botella y benchmarks) en vídeos verticales de corta duración (60–70s) optimizados algorítmicamente para plataformas como **YouTube Shorts** y **TikTok**.

El sistema elimina la fricción del trabajo editorial manual articulando investigación estructurada, síntesis de voz neuronal, generación cinemática procedimental y publicación programada a través de APIs oficiales.

---

## 🚀 Características Principales

* **Generación Editorial Guiada:** Redacción y estructuración automática de guiones técnicos mediante LLM (Gemini API), divididos en bloques de retención (*Hook*, *Technical Context*, *Deep Dive*, *Benchmark/Proof* y *Verdict/CTA*).
* **Motor de Síntesis Vocal (TTS):** Integración con ElevenLabs API utilizando locuciones neuronales de alta fidelidad, con normalización dinámica de volumen y control estricto de cadencia (WPM).
* **Subtitulado Cinético Word-Level:** Detección de silencios y alineación temporal exacta de cada palabra mediante `faster-whisper`, exportando metadatos para animaciones y *karaoke-style highlights*.
* **Composición Visual y Renderizado:**
  * Soporte multipreset visual (*Apple Liquid Glass*, *Schematic Paper / Technical Grid*, *Minimalist Neon Vector*).
  * Animación procedural de gráficos, diagramas de bloques y métricas de rendimiento en tiempo real vía FFmpeg / PIL.
  * Relación de aspecto nativa vertical 9:16 (1080x1920) a 60 FPS.
* **Distribución Multicanal Automatizada:** Integración directa con las APIs de YouTube Data v3 y TikTok Developer para subida desatendida, categorización y asignación de etiquetas/metadatos.
* **Control de Calidad y Verificación Local:** Scripts de telemetría y pruebas (`test_editorial_pipeline.py`) para validar límites de duración (cumplimiento de requisitos de monetización >60s), audio balanceado y renderizado antes del despliegue.

---

## 🏗 Arquitectura del Sistema

```text
[ Trigger / Topic ]
        │
        ▼
┌──────────────────┐
│  Gemini Engine   │ ──► Estructuración del guion técnico y metadatos
└────────┬─────────┘
         │
         ├──► [ ElevenLabs API ] ──► Audio Master (.mp3 / .wav)
         │                                    │
         │                                    ▼
         │                          [ faster-whisper ] ──► Subtítulos & Timestamps
         ▼                                                    │
┌──────────────────┐                                          │
│ Compositor / PIL │ ──► Generación de assets vectoriales / UI │
└────────┬─────────┘                                          │
         │                                                    │
         ▼                                                    │
┌─────────────────────────────────────────────────────────────┴┐
│                       FFmpeg Pipeline                        │
│             (Mezcla audiovisual, transiciones, HUD)          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                   [ Render Final: 1080x1920 ]
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
[ YouTube Shorts API ]                     [ TikTok Developer API ]
```

---

## 🛠 Requisitos Previos e Instalación

### Requisitos del Sistema
* **Python 3.10+**
* **FFmpeg** instalado y configurado en el `PATH` del sistema.

### Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/adrlopech/Silicon-Verdict.git
   cd Silicon-Verdict
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuración (.env)

Crea un archivo `.env` en la raíz del proyecto tomando como plantilla las siguientes variables de entorno:

```env
# Inteligencia Artificial & Síntesis de Voz
GEMINI_API_KEY="tu_clave_de_gemini"
ELEVENLABS_API_KEY="tu_clave_de_elevenlabs"
ELEVENLABS_VOICE_ID="id_de_la_voz"

# Credenciales de Publicación y Redes Sociales
YOUTUBE_CLIENT_SECRETS_FILE="client_secrets.json"
TIKTOK_ACCESS_TOKEN="tu_token_de_acceso_tiktok"

# Parámetros de Renderizado
DEFAULT_RENDER_STYLE="liquid_glass"  # liquid_glass | schematic_paper | neon_vector
TARGET_FPS=60
VIDEO_RESOLUTION="1080x1920"
```

---

## 💻 Uso

### 1. Generación y Renderizado Completo
Genera un vídeo completo a partir de un tema técnico específico:

```bash
python main.py --topic "Diferencias de arquitectura entre caché L2 y 3D V-Cache" --style liquid_glass
```

### 2. Pruebas y Validación Editorial
Ejecuta la suite de verificación local para validar coherencia textual, timings de voz y renderizado de prueba sin publicar en plataformas:

```bash
python scripts/test_editorial_pipeline.py --dry-run
```

---

## 📂 Estructura del Proyecto

```text
Silicon-Verdict/
├── assets/             # Fuentes tipográficas, overlays gráficos, clips base
├── config/             # Esquemas de configuración, temas visuales y reglas editoriales
├── modules/
│   ├── ai/             # Conectores LLM (Gemini) para análisis y guiones
│   ├── audio/          # Clientes TTS (ElevenLabs) y procesado de onda
│   ├── compositor/     # Motores de renderizado y layouts de motion graphics
│   ├── subtitles/      # Detección y parsing temporal con faster-whisper
│   └── uploader/       # Clientes OAuth para YouTube Data API y TikTok API
├── scripts/            # Scripts de diagnóstico, telemetría y pruebas unitarias
├── .env.example
├── main.py             # Entrypoint CLI del pipeline
├── requirements.txt
└── README.md
```

---

## 📄 Licencia

Distribuido bajo la licencia **MIT**. Para más detalles, consulta el archivo `LICENSE`.