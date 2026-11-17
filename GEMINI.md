# Silicon Verdict: instrucciones para Gemini / Antigravity

Este archivo era el manual del pipeline antiguo (vídeo máster de 60 FPS, menú de 5 opciones, presets Liquid Glass). Ese sistema ya no es el actual y su descripción se ha movido a
[`guide/legacy.md`](guide/legacy.md). Todo se produce ahora como **Motion Graphics** (tipografía cinética con voz, 62-90 s, 1080x1920 a 30 fps, en inglés).

Las instrucciones vigentes para un asistente son las de [`CLAUDE.md`](CLAUDE.md) y la documentación completa está en [`guide/`](guide/README.md).

## Resumen

- `genera`: lote automático de 4 vídeos de 4 formatos distintos, subida a YouTube privada con `publishAt` y programación en TikTok Studio, sin preguntar. Ver `guide/daily-workflow.md`.
- `limpieza`: `.venv/bin/python scripts/cleanup.py`.
- `help` / `ayuda`: `.venv/bin/python main.py help`.
- `corregir`: heredado del pipeline antiguo; el control de calidad actual (`qa_motion`) va dentro del pipeline.
- Formatos: myth, tier, whatif, easter, evolution, versus, hardware, simple, fix, decode, top5, eli5, fails, numbers, quiz, stop, rumor, review, news, any (`guide/formats.md`).
- Reglas: hashtags de una palabra pegada, vídeos de más de 60 s, nunca el canal de YouTube `@siliconverdict` ("Frame Floor"), commit y push directos a `main`.
