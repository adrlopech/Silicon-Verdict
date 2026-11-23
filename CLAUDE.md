# Silicon Verdict: instrucciones para el asistente

Estudio automático de vídeos verticales (Motion Graphics, 62-90 s, en inglés) para YouTube `@SiliconVerdictHQ` y TikTok `@siliconverdict`. La documentación completa está en [`guide/`](guide/README.md);
este archivo resume cómo operar el repositorio. El operador habla español; los vídeos, el código y la documentación están en inglés.

## Disparadores del chat

| Palabra | Qué hacer |
|---|---|
| `genera` (o `/genera`) | Flujo automático de 4 vídeos, **sin preguntar** (el operador ya autorizó publicar). Pasos exactos en `.claude/commands/genera.md`; explicación en `guide/daily-workflow.md` |
| `limpieza` | Ejecutar al instante `.venv/bin/python scripts/cleanup.py` y mostrar el balance (vídeos, carpetas temporales y MB liberados). Es lo único que vacía `output/tiktok/` y `output/tiktok_small/` |
| `help` / `ayuda` | Responder con la guía de comandos: este archivo, `guide/README.md` o `.venv/bin/python main.py help` |

"Los vídeos de hoy" significa `genera` con `--date` de hoy (fecha UTC) en lugar de mañana.

## Reglas fijas

- Hashtags de una sola palabra pegada (`#pcbuild`); en TikTok se eligen del desplegable.
- Los vídeos duran más de 60 s (monetización). Nunca se publica una voz robótica.
- Canales oficiales: YouTube `@SiliconVerdictHQ` (subcanal de la cuenta de Google NotChego) y TikTok `@siliconverdict`. **Nunca** el canal de YouTube `@siliconverdict` ("Frame Floor").
- Cambios de código: commit y push directos a `main`, sin ramas. No tocar los archivos ajenos a la tarea que ya estén modificados (`docs/.taste-skill/`, `skills-lock.json`, skills instaladas, `data/batch_*.json`).
- Cada vídeo lleva su portada: `render_cover` la crea, YouTube la recibe como miniatura y la de TikTok se sube a mano en TikTok Studio.
- La app de YouTube está en producción desde el 2026-11-23 (el token ya no debería caducar cada 7 días). Si falla con `invalid_grant`, renovar con `scripts/authenticate_yt.py` (cuenta NotChego, subcanal Silicon Verdict): `guide/publishing.md`. Pedir permiso al operador cada vez.
- Texto de la cámara: nunca aplicar transformaciones de cámara a la capa de texto (hace vibrar el texto).
- Evitar decimales en escenas `counter` (se redondean).

## Comandos esenciales

```bash
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan [--date AAAA-MM-DD] [--avoid fmt1,fmt2]
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py [--date AAAA-MM-DD]        # producir y programar en YouTube (tarda 10-20 min, ejecutar en segundo plano)
PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --topics reintento.json --out data/batch_retry.json   # rellenar un hueco que falló
.venv/bin/python main.py --motion-format <formato> [--export-only]
.venv/bin/python scripts/upload_existing.py "<video.mp4>" [--privacy private --publish-at 2026-11-17T13:00:00Z]
.venv/bin/python scripts/report_retention.py
PYTHONPATH=. .venv/bin/python scripts/health_check.py [--notify]   # token, voice credits, bank, prices, disk (genera_batch runs it and notifies when it ends)
.venv/bin/python -m pytest && .venv/bin/ruff check . && (cd remotion_studio && npx tsc --noEmit -p .)
```

Formatos (`--motion-format`): myth, tier, whatif, easter, evolution, versus, hardware, simple, fix, decode, top5, eli5, fails, numbers, quiz, stop, rumor, review, news, priced, any. Ver `guide/formats.md`.
Los guiones nuevos de formatos recientes (`fails`, `eli5`, `rumor`) a menudo no pasan los validadores: si un hueco falla, reintentar con un formato probado o con un guion escrito a mano en `data/scripts/`.

## Mapa del código

`main.py` (CLI, todo se produce como Motion) · `services/motion_generator.py` (esquema, prompts, validadores) · `services/motion_pipeline.py` (voz, render, portada, sonido, QA, subida) ·
`remotion_studio/src/motion/` (el vídeo) · `scripts/genera_batch.py` (lote de 4) · `services/youtube.py`, `yt_analytics.py` · `data/` (bases, manifiestos `batch_*.json`, guiones a mano) ·
`docs/` (portal público en GitHub Pages) · `guide/` (documentación) · `notes/` (notas privadas, no se versionan).

## Memoria y herramientas del operador

Las preferencias persistentes (publicar sin preguntar, cuentas, voz, formatos nuevos) viven en la memoria de Claude Code del proyecto. Para TikTok se usa Claude in Chrome sobre TikTok Studio; los pasos
y las trampas están en `guide/publishing.md`.
