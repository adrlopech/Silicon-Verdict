---
description: Genera 4 vídeos de Motion elegidos con los datos de YouTube/TikTok y los programa (por defecto para mañana; "de hoy" = fecha de hoy) en las mejores horas, con portada, en YouTube y TikTok
---

Ejecuta el flujo `genera` completo SIN preguntar nada (el usuario ya autorizó publicar). Explicación de cada paso: `guide/daily-workflow.md`; clics de TikTok Studio: `guide/publishing.md`.
Si el usuario pide "los de hoy", usa `--date` con la fecha UTC de hoy; si no, el lote es para mañana. Si pide analizar antes, lee los últimos 10 vídeos de YouTube (`scripts/report_retention.py` y `videos().list(part="statistics")`)
y de TikTok (`tiktokstudio/content`) y resume qué funciona.

0. Si la API de YouTube falla con `invalid_grant`, el token caducó (7 días): pide permiso y renuévalo (`guide/publishing.md#youtube-oauth`).
1. Plan: `PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan [--date AAAA-MM-DD] [--avoid formatos-de-ayer]`. Enséñalo en una tabla (hora UTC y Madrid, formato, motivo). Sale de YouTube Analytics + `data/batch_log.json`.
2. Produce y programa YouTube: `PYTHONPATH=. .venv/bin/python scripts/genera_batch.py [--date ...] [--avoid ...]` en segundo plano (10-20 min; no sondees). Renderiza 4 formatos distintos, sube cada uno a YouTube (SiliconVerdictHQ, privado + `publishAt`) con su portada como miniatura y escribe `data/batch_latest.json` (título, `caption`, `hashtags`, `tiktok_copy`, `cover`, hora).
   Si un hueco falla (`FAILED (nothing uploaded for this slot)`), relánzalo con `--topics` y `"slot"` fijo, `--out data/batch_retry.json`, usando un formato que suele pasar (evolution, versus, myth, whatif, hardware, decode, fix) o un guion a mano (`"script"`).
3. Verifica en YouTube (API): `privacyStatus` private y `publishAt` correcto en los 4.
4. TikTok (@siliconverdict, Claude in Chrome): por cada entrada, sigue los pasos de `guide/publishing.md#tiktok-studio-step-by-step`: subir `tiktok_copy`; descripción = `caption` + CADA hashtag escrito, esperar y elegido de la primera fila del desplegable (comprueba con JS que `.mention` los lista todos); subir `cover` en "Editar portada" y Guardar; "Programación" con la hora de Madrid del plan (el selector muestra GMT+1) y la fecha; "Programar" ("¿Seguir con la publicación?" → "Publicar ahora" continúa la programación).
   Comprueba en `tiktokstudio/content` que los 4 salen con su hora.
5. Informa al final: tabla con vídeo, formato, hora Madrid y enlace de YouTube, y avisa de lo que no se pudo comprobar (por ejemplo, que las miniaturas de YouTube no se vieron en Studio). Si ya hay un vídeo programado a la misma hora, mueve el nuevo.

Reglas fijas: hashtags de una sola palabra pegada; nunca el canal "Frame Floor" (`@siliconverdict` en YouTube); los vídeos duran más de 60 s; commit y push directos a `main` si cambias código.
