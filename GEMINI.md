# Operational Guidelines for 'Silicon Verdict'

## Arquitectura de Vídeo Máster Único (60-120s)
1. **Un Solo Render Máster por Ejecución:**
   - La arquitectura produce exactamente **un único archivo de vídeo vertical máster (1080x1920 @ 60 FPS)** con una duración estricta de entre 60 y 120 segundos (1-2 minutos).
   - Este vídeo cumple simultáneamente los requisitos de YouTube Shorts (indexación vertical hasta 3 min) y de TikTok (elegible para el Creator Rewards Program al superar los 60.5 segundos).
2. **Distribución Multi-Plataforma Desatendida:**
   - **YouTube:** Publicación directa en YouTube API v3 con estado público (`privacyStatus: "public"`).
   - **TikTok (Staging):** Se preserva una copia idéntica del archivo en `output/tiktok/<Título del vídeo>/<AAAA-MM-DD_HH-MM-SS>.mp4` (una carpeta por vídeo, con el título como nombre) junto a su archivo de metadatos `<AAAA-MM-DD_HH-MM-SS>.txt` en la misma carpeta con título optimizado, hashtags técnicos (#hardware #pcgaming #pcbuild #techtok #siliconverdict #benchmark) y guion estructurado por actos con timestamps para subida manual vía TikTok Studio Web.
3. **Audio y Narración:**
   - Pacing sereno y analítico con ElevenLabs: velocidad `0.92x`, `stability: 0.75`, `similarity_boost: 0.80`, `style: 0.12`.
   - Rotación estricta entre las 3 voces configuradas (`VOICE_1` Daniel, `VOICE_2` Adam, `VOICE_3` Liam) registrada en `data/history.db`.
4. **Cola de 30 Temáticas Verificadas (`topics_queue` en `data/history.db`):**
   - 30 temas de divulgación técnica profunda organizados en 4 bloques: Sensores y Cotidianos (A), Silicio y Microarquitectura (B), Redes y Protocolos (C), y Pantallas y Sensores Ópticos (D).
   - Cada tema sigue la estructura narrativa de 5 actos de alta retención: Gancho Contraintuitivo (0-8s) -> Solución Ingenua vs Real (8-25s) -> Magnitudes Humanas (25-55s) -> Causa Raíz de Ingeniería (55-85s) -> Remate Lapidario en Bucle (85-110s).

---

## Política de Preservación de TikTok y Limpieza de Disco
1. **Vídeos de TikTok (`output/tiktok/`):**
   - **NO se eliminan automáticamente** ni por tareas programadas en segundo plano, para permitir la subida manual tranquila del usuario.
   - Permanecen en `output/tiktok/` hasta que el usuario invoque explícitamente el comando **`limpieza`**.
2. **Comando "limpieza":**
   - Es el único disparador autorizado para vaciar la carpeta `output/tiktok/`.
   - Ejecuta de forma inmediata `scripts/cleanup.py` (o `scripts/cleanup_old_videos.py`).
   - Purga de forma atómica:
     * Todas las carpetas de vídeo de `output/tiktok/` (vídeo `.mp4`, metadatos `.txt` y portada `_cover.jpg`).
     * Todas las carpetas de vídeo de `output/youtube/` (vídeo y portada).
     * Todos los frames e imágenes en `temp/`.
     * Todas las pistas de audio intermedias en `temp/`.
     * Todas las carpetas temporales de render (`temp/run_*`, `/tmp/yt_automation/*`).
   - Preserva intactos: base de datos (`data/history.db`), tokens de autenticación (`data/*.json`), credenciales (`.env`).

---

## Protocolo de Disparo: "help" / "ayuda"
Cada vez que el usuario escriba la palabra **"help"** o **"ayuda"** en el chat:
1. **Respuesta Inmediata:**
   Responder directamente con la guía completa y estructurada del Command Center:
   - Lista de disparadores del chat (`genera`, `corregir`, `limpieza`, `help`).
   - Detalle de las 4 opciones temáticas del menú interactivo.
   - Comandos de terminal/CLI para ejecuciones directas y mantenimiento.
   - Rutas principales del repositorio (`output/`, `data/`).
2. **Equivalente en Terminal CLI:**
   ```bash
   .venv/bin/python main.py help
   ```
   *(o alternativamente: `.venv/bin/python scripts/help.py`)*

---

## Protocolo de Disparo: "limpieza"
Cada vez que el usuario escriba la palabra **"limpieza"** en el chat:
1. **Ejecución Inmediata:**
   Ejecutar automáticamente y al instante:
   ```bash
   .venv/bin/python scripts/cleanup.py
   ```
2. **Respuesta en Chat:**
   Mostrar el balance detallado con:
   - Número de vídeos eliminados (incluidos los de TikTok confirmados).
   - Frames e imágenes purgadas.
   - Pistas de audio y carpetas de render limpiadas.
   - Espacio total liberado en MB/GB.

---

## Protocolo de Disparo: "genera" (Flujo Guiado Interactivo de Dos Pasos)
Cuando el usuario escriba exactamente la palabra clave **"genera"** en la interfaz o chat de Antigravity:

1. **Paso 1: Despliegue del Menú de Selección (Suspensión de Ejecución)**
   El sistema **NO inicia la generación de inmediato**. Detiene la ejecución automática y responde al instante con este mensaje estructurado:

---
🎬 **Configuración de Producción — Silicon Verdict**

Selecciona el enfoque temático para este vídeo (60-120s):

1. **Hardware Deep Dive & Benchmarks** (Estilo Liquid Glass: Silicio, microarquitecturas, buses de memoria, telemetría técnica).
2. **Gaming & Optimización** (Estilo Liquid Glass: Rendimiento en juegos, presets competitivos, frametimes y 1% lows).
3. **Tech Curiosities & Storytelling** (Estilo Infográfico 2D: Paradojas de ingeniería, cables submarinos, satélites, física de chips).
4. **Automático (IA)** (La IA elige la categoría óptima basándose en la rotación de `data/history.db` y las analíticas de retención).
5. **Curiosidades en Minecraft** (Concepto técnico explicado dentro de Minecraft, ~64s, guion nuevo de Gemini).
6. **Motion Graphics** (Tipografía cinética con voz, 62-84s para monetizar, vertical 1080x1920, siempre en inglés. Al elegirla se pregunta el subgrupo: explainer clásico, curiosidades, juegos, Mito o Realidad, Tier List, ¿Y si…?, Evolución, Versus, Detalle oculto o Automático).

👉 Responde únicamente con el número deseado: **[1, 2, 3, 4, 5 o 6]**
---

2. **Paso 2: Procesamiento de la Selección y Ejecución**
   Tras recibir la respuesta del usuario:
   - **Si responde `1`**:
     * Asigna `category = "hardware_benchmarks"`.
     * Ejecuta: `.venv/bin/python main.py --category 1 --privacy public`
     * Aplica el layout Liquid Glass clásico, telemetría técnica de gran tamaño (96-120px) y B-Roll con filtros de exclusión estricta de componentes.
   - **Si responde `2`**:
     * Asigna `category = "gaming_benchmarks"`.
     * Ejecuta: `.venv/bin/python main.py --category 2 --privacy public`
     * Aplica métricas de juegos (FPS, 1% Lows) y B-Roll de gameplay correspondiente.
   - **Si responde `3`**:
     * Asigna `category = "tech_curiosities"`.
     * Ejecuta: `.venv/bin/python main.py --category 3 --privacy public`
     * Aplica el layout infográfico 2D esquemático (azules, grises, blancos y negros), ganchos paradójicos y estructura en 5 actos extraída de `topics_queue`.
   - **Si responde `4`**:
     * Asigna `category = "auto"`.
     * Ejecuta: `.venv/bin/python main.py --category 4 --privacy public`
     * Consulta `data/history.db` y los pesos de `data/category_weights.json` seleccionando automáticamente la categoría con mayor descanso de rotación.
   - **Si responde `5`**:
     * Ejecuta: `.venv/bin/python main.py --series minecraft --privacy public`
     * Pipeline `services/mc_pipeline.py`: siempre guion nuevo de Gemini (sin fallback); si Gemini no está disponible, el proceso se detiene.
   - **Si responde `6`** (Motion Graphics): **no ejecuta todavía**. Responde con este segundo menú y espera:

---
🎞️ **Motion Graphics — Subgrupo**

1. **Explainer clásico** (alterna curiosidad / juego; `auto`).
2. **Curiosidades tech** (una idea de hardware, código o IA con palabras, contadores y código).
3. **Juegos** (un hecho de ingeniería de un juego, con capturas y clips reales).
4. **Mito o Realidad** (afirmación popular + sello MYTH / FACT / PARTLY TRUE).
5. **Tier List** (ranking S-F que se llena ítem a ítem).
6. **¿Y si…?** (hipótesis sobre computación con consecuencias que escalan).
7. **Evolución** (líneas de tiempo con hitos y contadores de crecimiento).
8. **Versus** (dos contendientes, 3-5 rondas de barras).
9. **Detalle oculto de un juego** (footage real; solo hechos de la fuente).
10. **Arréglalo ya** (un síntoma que todos han sufrido y un ajuste exacto para arreglarlo; el cursor hace los clics).
11. **Decodificado** (qué significa de verdad el nombre o la etiqueta de un producto: RTX 5070 Ti, DDR5-6000 CL30, AX3000...).
12. **Automático** (la IA elige uno de los 11 temas anteriores, distinto del último vídeo de Motion Graphics).

👉 Responde únicamente con el número deseado: **[1 al 12]**
---

     Tras la respuesta ejecuta (siempre con `--series motion --privacy public`):
     * `1` → sin flags extra (alterna). `2` → `--motion-kind curiosity`. `3` → `--motion-kind game`.
     * `4` → `--motion-format myth`, `5` → `--motion-format tier`, `6` → `--motion-format whatif`, `7` → `--motion-format evolution`, `8` → `--motion-format versus`, `9` → `--motion-format easter`.
     * `10` → `--motion-format fix`, `11` → `--motion-format decode`.
     * `12` → `--motion-format any` (elige uno de los 11 temas con pesos —`FORMAT_WEIGHTS` en `services/motion_generator.py`: what-if, versus, evolución, fix y decode pesan 3, hardware 2, el resto 1—, excluye el del último vídeo y descarta los de juegos si no queda ningún juego con footage sin usar).
     * `9` es siempre un juego: necesita un juego con footage sin usar y dossier de fuentes; si no hay ninguno, el proceso se detiene y lo dice.
     * Entrada no válida en este segundo menú: *"Opción no válida. Introduce un número del 1 al 12."* y sigue esperando.
     * Los vídeos de juegos usan capturas y clips reales: cada elemento se usa una sola vez y se borra, y el juego queda bloqueado 14 días.
     * Estilo de retención (estudio `notes/content_style_study_2026-11.md`): `RETENTION_RULES` se añade al prompt de todo guion nuevo y `retention_problems()` lo valida (`make_validator(..., retention=True)`): apertura directa (la afirmación en ≤14 palabras, sin saludo ni "so/today/did you know"), un bucle abierto en las escenas 2-5 (una promesa que se cumple en el último tercio) y nunca tres titulares seguidos (`bigText`/`textWithAccent`). Los bancos escritos a mano no se obligan: `scripts/lint_retention.py` los mide y `scripts/upgrade_retention_bank.py` añadió el bucle abierto a los 60 guiones `fix`/`decode` aún sin publicar. whatif/versus/evolution quedan sin tocar como grupo de control del test de estilo.
* Pipeline `services/motion_pipeline.py`: guion JSON de Gemini (con respaldos), revisión de hechos, render con `@remotion/renderer`, sonido, control de calidad y subida. Cada formato tiene sus propias escenas (`tier`, `versus`, `verdict`, `timeline`), reglas y validadores en `services/motion_generator.py`. `fix` y `decode` salen de la investigación de nicho de nov. 2026 (`notes/niche_research_2026-11.md`) y reutilizan las escenas generales: exigen un `codeBlock` y un `list`, y el cursor (`fix`: 2+ escenas; `decode`: un `select` sobre la etiqueta).
   - **Entrada no válida**:
     * Si el usuario introduce cualquier otro carácter o texto, notifica:
       *"Opción no válida. Por favor, introduce 1, 2, 3, 4, 5 o 6 para continuar con 'genera'."*
       y mantiene la espera de una entrada válida.

3. **Acciones del Pipeline tras la Selección:**
   - Aplica el **guardarraíl de palabras de guion** (estrictamente entre 145 y 260 palabras) para asegurar que el máster dure exactamente entre 60 y 120 segundos.
   - Sintetiza la locución continua con ElevenLabs (0.92x, tono reflexivo y analítico).
   - Aplica de forma automática las reglas fonéticas aprendidas de `data/qa_rules.json` al generar subtítulos con Whisper.
   - Genera la **portada de alto CTR mobile-first** (`_cover.jpg`) a 1080x1920 con título masivo (88px), píldora de categoría y tinte 60%, insertándola como fotograma estático inicial en el Frame 00:00.00 (0.05s / 3 frames a 60 FPS) con compensación de audio de 50ms.
   - Renderiza el vídeo vertical 1080x1920 @ 60 FPS con diseño Apple Liquid Glass o Schematic Tech según corresponda, subtítulos cinéticos en cian eléctrico/blanco puro, y duración entre 60 y 120 segundos.
   - Guarda el archivo en `output/youtube/` y `output/tiktok/` junto con la portada `_cover.jpg` y el `.txt` de metadatos.
   - Sube a YouTube en modo público (`privacyStatus: "public"` si no es export-only).
   - Registra la telemetría completa de tokens, caracteres y coste estimado en la tabla `generation_metrics` de `data/history.db`.
   - Marca el tema como `completed` en `data/history.db`.

4. **Formato de Respuesta Estricto:**
   Responder única y exclusivamente con la plantilla requerida:

---
🚀 **Silicon Verdict Pipeline Completado**

**YouTube Short (Publicado):**
- Título: [Título del vídeo]
- Enlace público: https://youtube.com/shorts/[VIDEO_ID]

**TikTok (Listo para subida manual):**
- Archivo de vídeo: `output/tiktok/[nombre_archivo].mp4` (Duración: [XX.X]s | Peso: [XX.X] MB)
- Portada optimizada: `output/tiktok/[nombre_archivo]_cover.jpg`
- Archivo de metadatos: `output/tiktok/[nombre_archivo].txt`
- B-Roll seleccionado: [Nombre del clip o 'N/A (Schematic Tech)']
- Telemetría de coste: $[X.XXXX] USD ([X] chars ElevenLabs | [X] tokens Gemini)

📋 **Copiar y pegar para TikTok:**
**Título:**
[Título generado]

**Hashtags:**
#hardware #pcgaming #pcbuild #techtok #siliconverdict #benchmark

**Guion / Descripción:**
[Resumen o guion del vídeo]
---

## Protocolo de Disparo: "corregir" (Auditoría y Corrección Bajo Demanda)
Este sistema **NO se ejecuta de forma automática ni silenciosa** durante el proceso de producción habitual (`genera`). Debe activarse **única y exclusivamente** cuando el usuario escriba la palabra clave **"corregir"** en el chat de Antigravity.

1. **Paso 1: Auditoría Técnica Desatendida (Sin tocar archivos)**
   - Ejecutar:
     ```bash
     .venv/bin/python main.py --audit-latest
     ```
   - Localiza el último archivo `.mp4` generado en `output/tiktok/` y sus archivos asociados (`.txt`, `.ass`/`.srt`, audio).
   - Comprueba 4 dimensiones de QA:
     * **Subtítulos y Whisper:** Escaneo de errores fonéticos (`Siliconvertingt`, `TB.` por `te ve`, `14 to 40 p`, `Present -mont`, `PE Cores`), guiones huérfanos (`-STARVES`, `-RANGE`) y margen seguro inferior (`MarginV >= 384` para `Y <= 1536`).
     * **Niveles de Audio:** Análisis con `volumedetect` para `max_volume` y `mean_volume`, detectando clipping (`max_volume >= -0.5 dB`) y balance voz/música.
     * **Composición Visual y Metraje:** Legibilidad de telemetría (mínimo 96px para métricas), verificación de fotogramas iniciales congelados a 0 FPS y auditoría de la portada (`_cover.jpg` existente, 1080x1920 y contraste tipográfico).
     * **Estructura y Retención:** Duración total en la ventana óptima de 60 a 120 segundos y ausencia de banners intrusivos de suscripción en mitad del vídeo.

2. **Paso 2: Emisión del Reporte y Solicitud de Confirmación**
   - El agente detiene la ejecución inmediatamente y responde en el chat con la plantilla estricta:

---
📋 **Auditoría de Calidad: Último Vídeo Generado**
**Archivo analizado:** `output/tiktok/[nombre_del_video].mp4` (Duración: [XX.X]s)

**1. Errores Encontrados:**
- **Subtítulos / Whisper:** [Detalle de errores detectados o 'Sin fallos detectados']
- **Niveles de Audio:** [Detalle de clipping, saturación o balance o 'Niveles correctos']
- **Composición Visual:** [Fallos en B-roll, tamaños de fuente o estado cero o 'Composición correcta']
- **Estructura y Retención:** [Duración fuera de rango o presencia de banners invasivos o 'Correcto']

**2. Soluciones Propuestas para este Vídeo:**
- [Solución 1: ej. Corrección de términos en SRT y remux rápido sin recompilar vídeo]
- [Solución 2: ej. Ajuste de ganancia de audio a -22 dB en la pista de música]
- [Solución 3: ej. Actualización de data/qa_rules.json para prevenir el fallo en futuros vídeos]

⚠️ **Confirmación requerida:**
¿Deseas que aplique estas soluciones al vídeo actual y registre las reglas para las próximas ejecuciones? Responde **"Sí"**, **"No"** o indica instrucciones concretas.
---

3. **Paso 3: Acciones Post-Confirmación**
   - **Si el usuario responde "Sí" (o similar):**
     * Ejecutar:
       ```bash
       .venv/bin/python main.py --apply-fixes
       ```
     * Aplica las correcciones sobre el vídeo en `output/tiktok/` y `output/youtube/` (reensamblado con subtítulos corregidos o remux con atenuación de ganancia).
     * Actualiza el archivo de metadatos `.txt`.
     * Registra las reglas fonéticas y parámetros en `data/qa_rules.json` para que los futuros comandos `genera` las apliquen automáticamente.
     * Responde confirmando los cambios aplicados y la ruta del archivo corregido.
   - **Si el usuario responde "No" (o similar):**
     * Cancela la operación sin modificar ningún archivo en disco.
     * Informa al usuario de que no se ha realizado ninguna modificación.

---

## Matriz de Rotación Equilibrada (6 Días, 3 Pilares) y Presets Visuales

1. **Rotación Semanal en Tres Pilares:**
   - **Pilar 1: Hardware Benchmarks & Silicio (Técnico)**
     * Días: Lunes (Día 1) y Jueves (Día 4).
     * Categorías: `gpu_architecture`, `silicon_deep_dive`, `memory_buses`, `storage_pcie`.
     * Preset Visual: `liquid_glass` (Barras animadas de FPS, telemetría y b-roll difuminado).
   - **Pilar 2: Gaming & Optimización (Gamer / Noticias)**
     * Días: Martes (Día 2) y Viernes (Día 5).
     * Categorías: `gaming_benchmarks`, `fps_optimization`, `hardware_news`, `vram_and_buying_dilemmas`, `upscaling_tech`.
     * Preset Visual: `liquid_glass` (Gameplay dinámico, b-roll gamer, veredictos "Cómprala/Evítala").
   - **Pilar 3: Tech Curiosities & Infraestructura (Curiosidades / Ingeniería)**
     * Días: Miércoles (Día 3) y Sábado (Día 6).
     * Categoría: `tech_curiosities`.
     * Preset Visual: `schematic_tech` (Infografía técnica 2D oscura, lienzo cuadriculado 32px, diagramas esquemáticos vectoriales).

2. **Aislamiento Estricto del Preset `schematic_tech`:**
   - Se aplica **única y exclusivamente** a la categoría `tech_curiosities` (o con el flag `--preset schematic_tech`).
   - Las categorías de benchmarks y guías gamer conservan íntegramente el diseño Apple Liquid Glass con fondos de b-roll.
   - **Paleta de Color Exclusiva de Silicon Verdict:**
     * Fondo lienzo: Negro Obsidiana (`#07090E`) con viñeteado radial suave a Azul Medianoche (`#0F172A`).
     * Cuadrícula técnica: Gris Pizarra (`#1E293B`, 32px con puntos de cruce).
     * Líneas de interconexión: Gris Oscuro (`#334155`) y pulso en Azul Eléctrico (`#007AFF`).
     * Acento principal e información destacada: Azul Cian Eléctrico (`#38BDF8`).
     * Tipografía: Blanco Puro (`#FFFFFF`) con unidades y telemetría en Gris Frío (`#94A3B8`).
   - **Estructura Narrativa de 5 Actos (Storytelling de Ingeniería):**
     * Acto 1 (0-8s): Premisa Paradójica (Hook contraintuitivo).
     * Acto 2 (8-25s): Concepto Clave y Solución Ingenua vs Problema Real.
     * Acto 3 (25-55s): Traducción a Magnitudes Humanas y Analogía.
     * Acto 4 (55-85s): Causa Raíz de Ingeniería y Resolución Física.
     * Acto 5 (85-110s): Remate Lapidario y Cierre en Bucle.


---

## Subsistemas Avanzados de Producción, MLOps y Crecimiento

### 1. Generador Automático de Portada (*Cover Frame*) Mobile-First (`services/renderer.py`)
- **Generación Visual:**
  - Crea una imagen vertical de 1080x1920 (`output/tiktok/<Título>/<AAAA-MM-DD_HH-MM-SS>_cover.jpg` y copia en YouTube).
  - Fondo: Fotograma central del B-roll seleccionado o lienzo técnico oscuro con tinte negro al 60% (`rgba(0,0,0,0.60)`).
  - Título Hook Masivo: 84-98px en Roboto/Impact extra-bold, con resaltado de palabras clave en cian eléctrico (`#38BDF8`).
  - Badge Superior: Píldora de categoría en azul marino con borde cian (`rgba(15, 23, 42, 0.90)`).
  - Marca de Canal: Marca de agua discreta `@SiliconVerdict` con logotipo en la zona inferior segura.
- **Inserción en Frame 00:00.00:**
  - Se concatena al inicio exacto del MP4 durante 0.05s (3 frames a 60 FPS) mediante FFmpeg `concat` / `overlay`.
  - La pista de audio se retrasa 50ms (`adelay=50|50`) para mantener la sincronía labial y el ritmo del vídeo intactos.
  - Permite a TikTok y YouTube Shorts seleccionar automáticamente el fotograma 0 como miniatura de alto CTR.

### 2. Bucle de Retroalimentación Algorítmica (`scripts/analytics_sync.py`)
- **Sincronización de Retención de YouTube:**
  - Conecta con la YouTube Analytics API v3 y YouTube Data API v3 para recopilar `viewerPercentage`, `averageViewPercentage`, me gusta y comentarios de vídeos con más de 48 horas de vida.
  - Modo simulación disponible (`--simulate`) para entornos locales sin credenciales de canal en producción.
- **Cálculo de Score de Rendimiento:**
  $$\text{performance\_score} = (\text{viewerPercentage} \times 0.4) + (\text{averageViewPercentage} \times 0.6)$$
- **Calibración Dinámica de Pesos de Categorías (`data/category_weights.json`):**
  - La categoría con mayor rendimiento adquiere un 50% de probabilidad en el scheduler; las restantes se reparten un 25% equitativo.
- **Detección y Veto de Hooks Ineficaces:**
  - Si un vídeo tiene un abandono prematuro superior al 40% (*Swiped Away* > 40%), su estructura de gancho se registra en `data/qa_rules.json` bajo `ineffective_hooks` con penalización de probabilidad para evitar su repetición.

### 3. Guardarraíles de Consumo, Tokens y Costes
- **Guardarraíl Estricto de Palabras de Guion:**
  - Monitorea y recorta o expande el guion generado para situarlo estrictamente entre **145 y 260 palabras** (`enforce_script_word_guardrail` en `services/content_generator.py`), garantizando una duración de locución a 0.92x exactamente entre 60 y 120 segundos.
- **Telemetría y Control de Costes (`data/history.db` -> `generation_metrics`):**
  - Registra por cada vídeo: `run_id`, `topic_id`, `category`, `elevenlabs_characters`, `gemini_input_tokens`, `gemini_output_tokens`, `duration_seconds` y `estimated_cost_usd`.
  - Fórmula de coste real:
    $$\text{Cost} = (\text{Chars}_{ElevenLabs} \times 0.00030) + (\text{Tokens}_{Gemini} \times 0.000002)$$
  - Permite auditoría de costes históricos y optimización de márgenes operativos.

## Voz de respaldo local

Si ElevenLabs falla (sin créditos o sin red), `services/voice_synthesizer.py` y `services/tts.py` narran con un clon local de las mismas tres voces (VoxCPM2 8-bit en MLX vía VoiceStudio, pesos Apache-2.0, sin coste). Configuración: `TTS_BACKEND`, `LOCAL_TTS_FALLBACK` y `LOCAL_TTS_ENGINE` en `.env`; arranque con `scripts/voicestudio_server.sh`; muestras de referencia con `scripts/make_voice_refs.py`. Los modelos OmniVoice y NLLB de VoiceStudio son no comerciales: no usarlos.
