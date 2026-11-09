---
description: Genera 4 vídeos de Motion elegidos con los datos de YouTube/TikTok y los programa para mañana en las mejores horas (YouTube y TikTok)
---

Ejecuta el flujo `genera` completo SIN preguntar nada (el usuario ya autorizó publicar, ver memoria `upload-autonomy`):

1. Plan: `PYTHONPATH=. .venv/bin/python scripts/genera_batch.py --plan`. Enséñalo en una tabla (hora UTC y Madrid, formato, motivo). El plan sale de YouTube Analytics (retención media y vistas por formato, `scripts/report_retention.py`) + el historial de horas (`data/batch_log.json`).
2. Produce y programa YouTube: `PYTHONPATH=. .venv/bin/python scripts/genera_batch.py` (en segundo plano, tarda varios minutos; no sondees). Renderiza 4 formatos distintos, sube cada uno a YouTube (SiliconVerdictHQ, privado + `publishAt`) y escribe `data/batch_latest.json` con título, subtítulo de TikTok, hashtags, copia <10 MB y hora.
3. Verifica en YouTube (API: `privacyStatus` private y `publishAt` correcto en los 4).
4. TikTok (@siliconverdict, navegador Brave con la extensión Claude in Chrome): por cada entrada de `batch_latest.json`:
   - `https://www.tiktok.com/tiktokstudio/upload`, `find` "file input" y `file_upload` de `tiktok_copy`; espera ~8 s.
   - Descripción: clic en la caja, cmd+a, Delete, escribir `caption`; después CADA hashtag: escribirlo, esperar 3 s, clic en la primera fila del desplegable (~x=380,y=555). Comprueba con JS que `.mention` lista todos.
   - Bajar, "Programación", hora (la columna se centra en la hora actual; desplaza con scroll y elige hora y minuto) y fecha de mañana. TikTok Studio muestra GMT+0 Lisboa = UTC, así que usa la hora UTC del plan. Pulsa "Programar".
   - Comprueba en `tiktokstudio/content` que los 4 salen con su hora.
5. Informa al final: tabla con vídeo, formato, hora Madrid, enlace de YouTube, y avisa de lo que no se pudo comprobar. Si hay un vídeo ya programado a la misma hora, mueve el nuevo.

Reglas fijas: hashtags de una sola palabra pegada; nunca la cuenta NotChego ni el canal "Frame Floor"; los vídeos duran más de 60 s; commit y push directos a `main` si cambias código.
