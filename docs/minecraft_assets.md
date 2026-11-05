# Biblioteca local de assets de Minecraft (para vídeos estilo Minecraft)

Todo vive en `remotion_studio/public/` y está **ignorado por git** (los assets de Mojang y de los autores de los packs no se pueden redistribuir). Se regenera en cualquier máquina que tenga el juego y los packs:

```bash
python3 scripts/extract_minecraft_assets.py            # rutas por defecto de esta máquina
python3 scripts/extract_minecraft_assets.py --jar X.jar --pack otro.zip   # también --assets-dir y --asset-index para los sonidos
```

## Qué hay

| Carpeta | Contenido |
|---|---|
| `public/mc_assets/assets/minecraft/textures/` | 2.504 texturas del juego 1.20.1 (bloques, objetos, entidades, GUI, partículas, entorno, `destroy_stage_*`…) |
| `public/mc_assets/assets/minecraft/models/` · `blockstates/` | 3.691 modelos JSON y 1.005 blockstates |
| `public/mc_assets/assets/minecraft/font/` · `lang/` | fuentes, `en_us.json`, `es_es.json` |
| `public/mc_assets/INDEX.json` · `TEXTURES.txt` | catálogo y lista de todas las texturas (buscar con `grep`) |
| `public/mc_sounds/minecraft/sounds/` | 3.416 sonidos `.ogg` del juego (bloques, pasos, entidades, ambiente, música, ui…) con su nombre real, no el hash |
| `public/mc_sounds/minecraft/sounds.json` · `SOUNDS_INDEX.txt` | eventos del juego → archivos (p. ej. `block.chest.open: block/chest/open`, `block.stone.break: dig/stone1..4`); buscar con `grep` |
| `public/mc_packs/fresh_animations/` | Fresh Animations 1.11.2 (mobs: `optifine/cem/*.jem|jpm`, texturas) |
| `public/mc_packs/fa_objects/` | FA Objects 2.1.3 (cofres, shulker, balsas, minecart) |
| `public/mc_packs/fa_player/` | FA+Player 1.1 (`emf/cem/player.jem` + `a_player_*.jpm`) |
| `public/mc_packs/luma/` | projectLUMA 1.32 (shaders GLSL de OptiFine/Iris) |
| `public/mc/` | selección ya procesada que usa el vídeo (texturas con tinte de bioma aplicado, skin, iconos) |
| `public/mc_packs/player`, `chest` | copias planas de lo que carga el motor (`player.jem`, `chest.jem` y sus `.jpm`) |

Tintes de bioma: la hierba (`#91bd59`) y las hojas (`#77ab2f`) se tiñen al preparar `public/mc/` (`grass_top`, `grass_side`, `leaves`, `plant_grass`). Las texturas originales son en escala de grises.
Los sonidos no están en el jar: viven en `assets/objects` (por hash) y el script los copia con su nombre real usando `assets/indexes/5.json` (índice de la 1.20.1). Ocupan ~528 MB (la música es la mayor parte); si hace falta espacio se puede borrar `mc_sounds/minecraft/sounds/music` y se regenera con el script.

## Código del motor

Ver `docs/minecraft_video_kit.md` (kit modular en `remotion_studio/src/mc/`, un vídeo = un archivo de datos en `src/mc/episodes/`).

## Convenciones aprendidas (lo que costó descubrir)

**Mundo.** Un bloque = 1 unidad. Mallas fusionadas con atlas 4×4 de 16 px, caras ocultas entre bloques, sombreado vainilla (arriba 1, abajo 0.5, ±z 0.8, ±x 0.6) sustituido por luz estilo LUMA: ambiente `(0.6,0.75,1.0)` + sol `(1.0,0.9,0.8)` con oclusión ambiental por vértice y sombra del sol por vértice. Hojas opacas (relleno `#1f4a10` bajo la textura).

**Modelos `.jem` (EMF).** Eje de three.js = `(x, −y, −z)` del modelo vainilla (frente = +z).
- Piezas de nivel superior con caja: coordenadas **absolutas** (`x` espejado, `y` hacia arriba). Piezas anidadas: coordenadas **relativas** a su pivote, `y` hacia abajo.
- `translate` estático = `(tx, −ty, −tz)` relativo al padre.
- Las salidas `tx/ty/tz` de las animaciones son posiciones **absolutas** del pivote: en piezas vainilla (`head`, `body`, brazos, piernas…) en el sistema vainilla (`y_three = 24 − ty`); en piezas propias del pack en el sistema del `.jem` (`y_three = ty`, `z_three = −tz`).
- Rotaciones: orden `ZYX`, `(rx, −ry, −rz)`; en piezas propias (ejes invertidos) el signo de `rx` es el contrario.
- Cajas de piezas propias: las regiones de textura "arriba" y "abajo" van intercambiadas.
- `sizeAdd` infla la caja `2·sizeAdd` px (capas de la skin).

**Animaciones.** Se usan las animaciones vainilla de Minecraft 1.20 suavizadas (`src/mc/anim.ts`, coreografía automática en `src/mc/choreo.ts`); las de Fresh Animations se descartaron (daban pose rota y temblor al evaluarse fuera del juego). El evaluador de `.jem/.jpm` queda en `src/mc/experimental/emf.ts` sin usar. Lo aprendido de FA: sus animaciones leen los valores vainilla de cada hueso, `tx/ty/tz` son posiciones absolutas, `random(id)` debe ser constante y el estado de las variables persiste entre fotogramas.

**Cámara y transiciones.** `src/mc/camera.tsx`: pocos planos largos con movimiento propio; entre ellos zoom-in/zoom-out de 12 fotogramas por lado (campo de visión −28 %, desenfoque 2,5 px). Más cortes o zooms más rápidos marean.

**Postproceso.** `LumaTonemap` (Uncharted 2 + saturación, de `final.fsh` de LUMA), bloom suave y viñeta. Los shaders originales de LUMA no se ejecutan en three.js (usan buffers de OptiFine); se portaron sus parámetros.

## Sonidos útiles para estos vídeos

`block.stone.break` (picar), `block.stone.hit`, `entity.player.attack.weak|strong`, `entity.item.pickup` (recoger objeto), `entity.experience_orb.pickup`, `block.chest.open|close`, `block.grass.step`/`block.stone.step` (pasos), `block.amethyst_block.chime`, `ambient.cave`, `ui.button.click`, `entity.player.levelup`. El kit los usa por nombre de evento (`{f, event:'block.chest.open'}`) y ya coloca solo pasos, golpes, roturas, recogida, ataques y cofre.

## Para crear un vídeo nuevo

Sigue `docs/minecraft_video_kit.md` (los vídeos de la app salen de guiones nuevos de Gemini; para uno a mano, copiar `src/mc/episodes/actionsDemo.ts`).
