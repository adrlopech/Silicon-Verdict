# Kit de vídeos estilo Minecraft (Remotion)

Todo lo aprendido iterando el vídeo "La RAM, explicada" está en un kit reutilizable en `remotion_studio/src/mc/`. Un vídeo nuevo es **un archivo de datos** (`episodes/<nombre>.ts`); las animaciones, los sonidos, la sincronización y las transiciones salen solos.

```
src/mc/
  core.tsx      assets, matemáticas (smoothstep, ramp...), iluminación estilo LUMA, TexBox (cajas con textura), sprites de objetos
  world.tsx     terreno fusionado con AO y sombras de sol por vértice, árboles, plantas, nubes, sombra real del sol
  choreo.ts     coreografía: plan de pasos -> pista por fotograma (rutas, giros, acciones, eventos)
  kinds.ts      tabla por tipo de actor: hitbox vainilla, escala del modelo, pierna, amplitud, zancada sin patinar, prioridad
  collision.ts  hitboxes: rutas A* alrededor de sólidos, empujones entre actores, golpes con retroceso
  solids.ts     sólidos del episodio (colinas, troncos, cofre, carteles, escalera, marco y hoja de puerta, vetas)
  anim.ts       animaciones vainilla suavizadas (humanoide, cuadrúpedo, gallina)
  actors.tsx    Humanoid (jugador, zombi, esqueleto), Mob (cerdo, vaca, gallina, creeper)
  props.tsx     cofre, carteles, veta de mineral (grietas + partículas + drops)
  camera.tsx    planos, transición zoom-in/zoom-out, rig
  sfx.tsx       sonidos por evento del juego ("block.chest.open")
  hud.tsx       hotbar, subtítulos      post.tsx   profundidad de campo + bloom + tonemapping LUMA + viñeta
  episode.tsx   EpisodeSpec + composición genérica + validador
  director.ts   guion JSON -> EpisodeSpec (layout, coreografía, cámara, props, sonidos) · story.tsx composición McStory
  episodes/     actionsDemo.ts (nadar, puerta, escalera; plantilla para episodios a mano) · mobsDemo.ts (prueba de todos los mobs)
  experimental/ emf.ts (evaluador de .jem/.jpm de Fresh Animations; sin usar)
```

Registro en `src/Root.tsx`: `McStory` (vídeos generados), `McMobsDemo` y `McActionsDemo` (`<Composition ... defaultProps={{ spec: actionsDemo }} />`).
Render de un episodio a mano: `cd remotion_studio && npx remotion render src/index.ts McActionsDemo ../output/actions.mp4` (los vídeos de la app: `main.py --series minecraft`)
Fotograma suelto: `npx remotion still src/index.ts McActionsDemo out.png --frame=120`

## Crear un vídeo nuevo

1. Copia `episodes/actionsDemo.ts` y cambia el guion (`beats`), el mundo (`world`), los actores y los props.
2. Describe a cada actor con un **plan** de pasos, no con posiciones por fotograma:

| Paso | Qué hace |
|---|---|
| `{t:'wait', frames}` | se queda quieto (respira) |
| `{t:'walk', to:[x,z], via?, speed?}` | camina a 4.1 bloques/s (sprint: `speed: 5.6`); ruta redondeada, rodea `obstacles` solo, gira antes de arrancar |
| `{t:'face', to: ángulo\|[x,z], frames?, dir?:'front'}` | giro en el sitio (16-40 fotogramas, `'front'` = pasa de cara a la cámara en giros de 180°) |
| `{t:'act', kind, frames, cycle?, look?}` | `mine` (picar, 16 f/golpe), `attack` (12), `reach` (alcanzar, p. ej. cofre), `wave` (saludar), `use` (comer/beber), `jump` (salto de ~1,1 bloques en el sitio; el aterrizaje suena como un paso), `climb` (con `rise`: bloques que sube, negativo baja; ~2,3 bloques/s) |
| `{t:'walk', to, swim:true}` | `swim` solo fija la velocidad por defecto (1,9 bloques/s). **Nadar depende de la posición**: el actor nada mientras está dentro de un estanque (`world.ponds`), con transición gradual en la orilla; chapoteo al entrar y brazadas con sonido. Termina el tramo `swim` dentro del agua y sigue con un `walk` normal |

   Mundo: `world.ponds: [[x0,z0,x1,z1,profundidad]]` excava estanques con agua animada (textura vainilla, 32 fotogramas).
   Ángulos: `0` = mira a +z (hacia la cámara por defecto), `π/2` = +x. Los eventos (pasos, golpes, roturas) se calculan de la pista.
   `obstacles` ya no hace falta para los props ni los árboles: el episodio añade solo todos los sólidos (ver "Hitboxes").
3. Props: `door` (puerta en un marco de tablones de 3 de ancho: `at` = centro del hueco, `rotY`, `openAt`/`closeAt`, `swing:±1`; el actor debe esquivar el marco con `obstacles`), `ladder` (columna de tablones con escalera en su cara +z; `height`, `rotY`), `sign` (carteles fijos en el mundo), `chest` (`openAt`/`closeAt`; deriva los tiempos de `track.marks`/`acts`, como la puerta de `actionsDemo.ts`), `vein` (veta que el actor pica: cada golpe agrieta y rompe un bloque, suelta partículas y el objeto vuela al hotbar).
4. Opciones del episodio: `dof` (profundidad de campo estilo tráiler, 2 por defecto, 0 la apaga), `hand` del actor como lista `[{f, item}]` para cambiar de objeto, `hotbar.selected: [{f, slot}]` para cambiar de casilla.
5. Planos (`shots`): pocos y largos; `follow:'id'` sigue a un actor (posición de cámara y de mirada = desplazamiento respecto al actor, x y z); `eased:true` para panorámicas.
6. Sonidos: automáticos para pasos, golpes, roturas, recogida, ataques y cofre. Extras en `sounds: [{f, event:'entity.pig.ambient'}]` con nombres del juego (`public/mc_sounds/SOUNDS_INDEX.txt`, `public/mc/sound_events.json`).
7. Valida sin renderizar con `node scripts/validate_episodes.mjs` (añade tu episodio en `src/mc/cli.ts`) y revisa fotogramas con `still` antes de renderizar.

## Reglas que salieron de probar (el validador comprueba las marcadas ✔)

- **Ritmo:** caminar a ~4.1 bloques/s; más rápido parece a x2 ✔. La amplitud de brazos y piernas sigue la velocidad real.
- **Giros:** 16-40 fotogramas con smoothstep, la cabeza se adelanta; nunca giros de 12 fotogramas.
- **Hitboxes:** ningún actor atraviesa bloques ni a otro actor; el validador avisa si pasa ✔ (ver "Hitboxes").
- **Cámara:** un corte cada ~3 s como máximo ✔, planos ≥ 60 fotogramas ✔, transición de 12 fotogramas por lado con fov −28 % (más rápido o más corto marea).
- **Capas transparentes auxiliares** (receptor de sombras, etc.) con `depthWrite={false}`: si escriben profundidad tapan el agua y todo lo que queda por debajo.
- **Puertas:** gira hacia la cámara (`swing:1`, por defecto); hacia dentro queda oculta tras la pared y parece que desaparece.
- **Subtítulos:** el contenedor con `transform` debe ser `position:absolute; inset:0`; si no, el texto sale de pantalla.
- **HUD:** solo hotbar (sin vida, hambre ni XP). Carteles fijos en el mundo.
- **Sonido:** los pasos vainilla son ~30× más bajos que golpes y roturas: usa siempre `block.<superficie>.step`, que carga copias normalizadas (`public/mc/sfx/`). No pongas la música del juego (derechos).
- **Texturas del cofre:** arriba/abajo intercambiados en cajas tipo cofre (`swapVert`); skeleton y similares reutilizan UV con `mirror`.

## Hitboxes y colisiones

Cada actor tiene la hitbox vainilla de su tipo (`kinds.ts`: jugador 0,6×1,8, cerdo 0,9×0,9, araña 1,4×0,9...) y todo lo sólido del mundo tiene la suya (`solids.ts`): colinas, troncos, cofre, carteles, columna de la escalera, marco de la puerta, bloques de mineral (hasta que se rompen) y la hoja de la puerta (solo mientras está cerrada).

- **Rutas:** `walk` va recto si nada estorba; si no, A* en una rejilla de 0,25 bloques con los sólidos inflados por el radio del actor, recortado a pocos tramos rectos y con esquinas redondeadas que nunca se meten en un sólido. Las rutas se cachean (el director recalcula muchas veces).
- **Entre actores:** si dos hitboxes se solapan, cede el de menor prioridad (jugador 3, otros humanoides y aldeano 2, mobs 1), como el empujón vainilla. La corrección se suaviza en el tiempo: el mob se aparta antes del contacto en vez de saltar, mueve las patas al ser empujado y no acaba dentro de un bloque.
- **Golpes:** cada golpe de `attack` alcanza al actor más cercano delante (≤3 bloques): destello rojo 15 fotogramas, retroceso de 0,45 bloques con un saltito y sonido `entity.<mob>.hurt`; invulnerable 15 fotogramas como en el juego.
- **Agua:** los actores que nunca nadan (mobs) rodean los estanques (`avoidWater`).
- **Validador:** `collisionReport` comprueba solapes entre actores, actores dentro de sólidos (respetando cuándo existen) y cámara dentro de un actor o un bloque. En `mc_compile` sale aparte como `quality` (no hace rechazar el guion de Gemini).

## Animaciones incluidas (todas vainilla 1.20 suavizadas)

- **Pies sin patinar:** la zancada (`kinds.ts › noSlipStride`) se calcula de la longitud de la pierna y la amplitud, y la cadera baja cuando las piernas se abren, así los pies no resbalan ni flotan. Escala vainilla: jugador y aldeano 0,9375; zombi, esqueleto y mobs a 1 px = 1/16 de bloque.
- **Mirada:** mobs y aldeanos giran la cabeza (suave, ±0,9 rad) hacia el jugador cuando está a menos de ~6 bloques.
- **Humanoide** (`anim.ts › humanoidPose`): idle con respiración, caminar, correr (inclinación y zancada mayores), agacharse (`sneak`), saltar, picar/atacar (animación de ataque vainilla con ciclo configurable), alcanzar, saludar, comer/beber, brazos al frente de zombi.
- **Cuadrúpedos** (cerdo, vaca, oveja con lana) y **creeper**: patas en diagonal, balanceo de cabeza, rebote, `swell` del creeper.
- **Aldeano** (brazos cruzados, balanceo de cabeza; textura base sin profesión) y **arañas** (`spider`, `cave_spider`: ocho patas en cuatro pares desfasados).
- **Nadar** (cuerpo plano, brazadas alternas, patada de piernas, el cuerpo se hunde hasta la superficie), **trepar** (manos alternas por encima de la cabeza, rodillas que suben) y **puerta** (giro suave con ángulo vainilla).
- **Gallina:** patas, aleteo suave, picoteo de cabeza.
- **Cofre:** tapa vainilla con asentamiento. **Mineral:** 10 etapas de grietas, partículas, objeto que cae y vuela al jugador.
- **No incluido todavía:** otros mobs (lobo, gato, caballo, enderman...), oveja de otros colores (solo lana blanca), aldeano con profesión, bloques redstone, construir bloques. Añadir un mob = una entrada en la tabla `MOBS` de `actors.tsx` (con `tex`/`inflate` por caja para capas como la lana) (pivote, cajas y UV del modelo vainilla) y su textura en `scripts/extract_minecraft_assets.py › MOBS`.

## Rendimiento

Geometrías de caja y materiales se crean una vez y se comparten (`core.tsx`: caché por tamaño/UV/escala y por textura/tinte); antes cada caja de cada actor creaba una geometría nueva en cada fotograma. El mundo se voxeliza una vez por episodio (terreno, plantas y colisiones comparten el mapa), el agua es una sola malla y el director memoriza la duración de cada plan. Compilar un guion de 64 s: ~50 ms.

## Medir el movimiento sin verlo

`python3 scripts/analyze_motion.py output/video.mp4 --cuts 60,170,232` decodifica el vídeo y, por plano, mide: saltos bruscos entre fotogramas (`pops`: temblores, teletransportes, parpadeos), nitidez del sujeto frente al fondo (`dof subj/bg` > 1,3 = el fondo está desenfocado de verdad), estabilidad del enfoque (`pump`) y qué tan limpia es cada transición. Resultado actual: 0 saltos en los tres vídeos de ejemplo, enfoque estable y un único salto por corte.

## Assets

`python3 scripts/extract_minecraft_assets.py` recrea todo desde tu instalación del juego y los packs: texturas/modelos (`public/mc_assets`), sonidos (`public/mc_sounds`), selección procesada con tintes de bioma (`public/mc`), catálogo de eventos de sonido y pasos normalizados. Ver `docs/minecraft_assets.md`.

## Guiones y generador (serie `minecraft` de la aplicación)

Además de escribir un episodio a mano, el kit compila un **guion JSON** (`src/mc/director.ts`) a un `EpisodeSpec` completo. El guion dice *qué* pasa; el director decide *cómo*: distribución del mundo, rutas, giros, cámara, props, sonidos, objeto en la mano, hotbar y subtítulos.

```
Gemini ─▶ McStory (core/schemas.py) ─▶ services/mc_director.py (compila con node, valida) ─▶ services/mc_renderer.py (Remotion McStory)
          services/mc_story_generator.py       scripts/mc_compile.mjs                         services/mc_pipeline.py (carpetas, metadatos, YouTube)
```

**Formato del guion** (`remotion_studio/mc_scripts/studio_preview.json` es un ejemplo mínimo, solo para previsualizar en Remotion Studio):
- `stations`: lugares en orden de izquierda a derecha: `sign`, `mine` (veta de minerales, máx. 2 `mine` por estación), `chest` (1 apertura), `pond` (nadar), `door`, `ladder` (poner la última), `pen` (mobs). Cualquiera puede llevar `label` (cartel de ≤4 líneas).
- `beats`: 12-16 por vídeo de 64 s; `text` (subtítulo ≤60 caracteres), `hl`, `seconds` mínimo, `shot` (`sign|close|orbit|wide|follow|pan`, opcional), `focus`, `actions` y `sound`.
- `actions`: `go, sprint, mine, open_chest, swim, open_door, climb, wave, jump, use, attack, look, wait`. El director camina solo hasta la estación, se gira hacia ella y actúa. Un beat dura lo que tarde su acción más lenta; todos los actores esperan al más lento.
- `cast`: actores extra (aldeano, zombi...) que obedecen acciones con `actor`. `inventory.grow_at_beat`: aparece la segunda fila de la hotbar.
- `seconds`: el director nunca produce menos (alarga con pausas y mantiene el último plano). La serie de la app usa **64 s** (TikTok solo monetiza > 60 s) y el generador rechaza guiones de menos de 61 s o más de 80 s.

**Cámara automática:** planos ≥90 fotogramas (un corte cada ~3 s); un tramo de más de ~7 s se parte (cortando donde el héroe empieza otro paso). Si no hay `shot`: el primero enfoca el cartel; un trayecto largo es `pan` la primera vez y `follow` después; nadar y trepar tienen su plano propio; los tramos quietos alternan órbita, plano general y plano cercano, siempre desde el lado de la cara del sujeto (tres cuartos, o de lado si está trabajando para que se vea también el objetivo). Cada plano candidato se descarta si la cámara roza un actor, entra en un bloque, o un bloque alto u otro actor tapa al sujeto; se elige el primero limpio (o el de menos problemas, alejándose si hace falta). Las plantas no crecen en el recorrido de la cámara.

**Comandos**
```bash
node scripts/mc_compile.mjs remotion_studio/mc_scripts/studio_preview.json   # compila y valida (JSON con errores/avisos/quality, duración)
.venv/bin/python scripts/test_mc_director.py                         # pruebas del director
cd remotion_studio && npx remotion still src/index.ts McStory out.png --frame=60 --props=props.json   # props.json = {"script": {...}}
.venv/bin/python main.py --series minecraft --export-only            # vídeo completo (guion del banco o Gemini) en output/
.venv/bin/python main.py --series minecraft --topic "la caché" --export-only
.venv/bin/python scripts/refill_story_bank.py --series minecraft --target 10   # llena el banco de guiones
```
Sin `--export-only` el vídeo se sube a YouTube (igual que el resto de series). **Cada vídeo usa un guion nuevo de Gemini**: primero uno del banco (guiones que Gemini escribió por adelantado y nunca se han usado), si no, uno en vivo. No hay guion de emergencia escrito a mano: si Gemini no responde y el banco está vacío, no se genera vídeo (`McScriptUnavailable`) y hay que rellenar el banco. Todo el texto de pantalla, título y metadatos va **en inglés** (`MC_LANGUAGE=en` por defecto; `es` solo si algún día se quiere).

**Actores extra (`cast`)** se colocan al lado del héroe (detrás, lejos de la cámara), nunca en su mismo punto. Los mobs de un corral se reparten según su hitbox.

**Límites actuales:** un solo héroe jugador con pico/espada automáticos; mundo de hierba (el ruido de pasos sí cambia con `surface`); estaciones dispuestas en línea recta. Para algo fuera del vocabulario se escribe un episodio a mano (secciones anteriores).
