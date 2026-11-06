#!/usr/bin/env python3
"""Rebuild the local Minecraft asset library used by the Remotion Minecraft-style videos.

Copies, from the user's OWN game install and downloaded packs, everything the video engine can use:

  remotion_studio/public/mc_assets/   -> full textures, models, blockstates, fonts, lang (from the game jar)
  remotion_studio/public/mc_sounds/   -> every game sound (.ogg) under its real name + sounds.json event map + SOUNDS_INDEX.txt
  remotion_studio/public/mc/          -> the processed selection the video kit loads: tinted textures, mobs, items, HUD icons,
                                         sound_events.json (event -> files) and sfx/ (normalised footstep sounds)
  remotion_studio/public/mc_packs/    -> complete resource/shader packs (Fresh Animations, FA Objects, FA+Player, LUMA)
  remotion_studio/public/mc_assets/INDEX.json + TEXTURES.txt -> searchable catalogue

All of it is git-ignored (Mojang / pack-author assets are not redistributable). Run this on any machine
that has the game and the packs to recreate the library.

Usage:
  python3 scripts/extract_minecraft_assets.py                      # default paths of this machine
  python3 scripts/extract_minecraft_assets.py --jar X.jar --pack A.zip --pack B.zip
"""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "remotion_studio" / "public"
DEFAULT_JAR = Path("/Users/Chego/Documents/curseforge/minecraft/Install/versions/1.20.1/1.20.1.jar")
DEFAULT_ASSETS = Path("/Users/Chego/Documents/curseforge/minecraft/Install/assets")  # holds indexes/ and objects/
DEFAULT_INDEX = "5"  # asset index used by 1.20.1
DEFAULT_PACKS = {
    "fa_objects": Path("/Users/Chego/Downloads/FA-Objects-v2.1.3.zip"),
    "fa_player": Path("/Users/Chego/Downloads/FA+Player-v1.1.zip"),
    "fresh_animations": Path("/Users/Chego/Downloads/FreshAnimations_v1.11.2_1.20.zip"),
    "luma": Path("/Users/Chego/Downloads/projectLUMA - v1.32.zip"),
}
JAR_PREFIXES = (
    "assets/minecraft/textures/",
    "assets/minecraft/models/",
    "assets/minecraft/blockstates/",
    "assets/minecraft/font/",
    "assets/minecraft/lang/en_us.json",
    "assets/minecraft/lang/es_es.json",
    "assets/minecraft/atlases/",
)


def extract_jar(jar: Path, out: Path) -> int:
    n = 0
    with zipfile.ZipFile(jar) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.startswith(JAR_PREFIXES):
                continue
            dest = out / info.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(info))
            n += 1
    return n


def extract_pack(zip_path: Path, out: Path) -> int:
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir() or ".." in info.filename:
                continue
            dest = out / info.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(info))
            n += 1
            # LUMA ships its real pack as a nested zip inside the download
            if info.filename.lower().endswith(".zip"):
                nested = dest.with_suffix("")
                with zipfile.ZipFile(dest) as nz:
                    nz.extractall(nested)
    return n


def extract_sounds(assets_dir: Path, index_name: str, out: Path) -> int:
    """Sounds are stored by hash in assets/objects; the index maps real names -> hashes."""
    index = json.loads((assets_dir / "indexes" / f"{index_name}.json").read_text())["objects"]
    n = 0
    for name, meta in index.items():
        if not (name.startswith("minecraft/sounds/") or name == "minecraft/sounds.json"):
            continue
        src = assets_dir / "objects" / meta["hash"][:2] / meta["hash"]
        if not src.exists():
            continue
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        n += 1
    # event -> files catalogue, e.g. "block.chest.open: block/chest/open1 block/chest/open2 ..."
    events = json.loads((out / "minecraft" / "sounds.json").read_text())
    lines = []
    for event in sorted(events):
        files = [s["name"] if isinstance(s, dict) else s for s in events[event].get("sounds", [])]
        lines.append(f"{event}: " + " ".join(f.replace("minecraft:", "") for f in files))
    (out / "SOUNDS_INDEX.txt").write_text("\n".join(lines) + "\n")
    return n


def build_index(assets: Path) -> None:
    tex_root = assets / "assets" / "minecraft" / "textures"
    index = {"textures": {}, "models": 0, "blockstates": 0}
    lines = []
    for p in sorted(tex_root.rglob("*.png")):
        rel = p.relative_to(tex_root).as_posix()
        cat = rel.split("/")[0]
        index["textures"][cat] = index["textures"].get(cat, 0) + 1
        lines.append(rel)
    index["models"] = len(list((assets / "assets" / "minecraft" / "models").rglob("*.json")))
    index["blockstates"] = len(list((assets / "assets" / "minecraft" / "blockstates").rglob("*.json")))
    (assets / "INDEX.json").write_text(json.dumps(index, indent=2))
    (assets / "TEXTURES.txt").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------------------------------------------------
# Processed selection used by remotion_studio/src/mc (biome tints applied, vanilla names -> kit names)
# ---------------------------------------------------------------------------------------------------------------------
GRASS_TINT = "#91bd59"
FOLIAGE_TINT = "#77ab2f"
ITEMS = ["diamond_pickaxe", "iron_pickaxe", "iron_sword", "coal", "raw_iron", "gold_ingot", "redstone", "lapis_lazuli", "diamond", "apple", "stick", "emerald", "bread", "diamond_sword", "wheat", "book", "writable_book", "paper"]
BLOCKS_COPY = ["ladder", "dirt", "stone", "oak_planks", "oak_log", "oak_log_top", "dirt_path_top", "dirt_path_side", "coal_ore", "iron_ore", "gold_ore", "redstone_ore", "lapis_ore", "diamond_ore", "torch", "red_wool", "white_wool", "barrel_side", "barrel_top", "hay_block_side", "crafting_table_front", "bookshelf"]
MOBS = {"mob_zombie": "entity/zombie/zombie", "mob_skeleton": "entity/skeleton/skeleton", "mob_creeper": "entity/creeper/creeper",
        "mob_pig": "entity/pig/pig", "mob_cow": "entity/cow/cow", "mob_chicken": "entity/chicken",
        "mob_sheep": "entity/sheep/sheep", "mob_sheep_fur": "entity/sheep/sheep_fur", "mob_spider": "entity/spider/spider",
        "mob_cave_spider": "entity/spider/cave_spider", "mob_villager": "entity/villager/villager"}
PROFESSIONS = ["farmer", "librarian", "toolsmith", "cleric", "fisherman", "mason", "cartographer", "armorer"]
PLAYER_SKINS = ["alex", "ari", "efe", "kai", "makena", "noor", "sunny", "zuri"]
WATER_TINT = "#3f76e4"
PLANT_COPY = ["poppy", "dandelion", "azure_bluet", "oxeye_daisy"]


def tint(img, hex_color):
    from PIL import Image  # noqa: F401
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            R, G, B, A = px[x, y]
            px[x, y] = (R * r // 255, G * g // 255, B * b // 255, A)
    return img


def import_extra_skins(out) -> None:
    """Skins from assets/skins/*/ (NameMC...) -> public/mc/skin_<name>.png. Slim (3 px) arms are widened to the classic 4 px arms of the kit's player model."""
    from PIL import Image
    for src in sorted((ROOT / "assets" / "skins").glob("*/*.png")):
        im = Image.open(src).convert("RGBA")
        if im.size != (64, 64):
            print(f"  skin {src.name}: not 64x64, skipped")
            continue
        slim = all(im.getpixel((x, y))[3] == 0 for x in (54, 55) for y in range(20, 32))
        if slim:  # arm boxes: right (40,16) + overlay (40,32), left (32,48) + overlay (48,48)
            for ox, oy in ((40, 16), (40, 32), (32, 48), (48, 48)):
                regions = {  # slim face -> (x, y, w, h) and where the classic layout puts it
                    "top": ((ox + 4, oy, 3, 4), (ox + 4, oy)), "bottom": ((ox + 7, oy, 3, 4), (ox + 8, oy)),
                    "right": ((ox, oy + 4, 4, 12), (ox, oy + 4)), "front": ((ox + 4, oy + 4, 3, 12), (ox + 4, oy + 4)),
                    "left": ((ox + 7, oy + 4, 4, 12), (ox + 8, oy + 4)), "back": ((ox + 11, oy + 4, 3, 12), (ox + 12, oy + 4)),
                }
                crops = {k: im.crop((a, b, a + w, b + h)) for k, ((a, b, w, h), _) in regions.items()}
                im.paste((0, 0, 0, 0), (ox, oy, ox + 16, oy + 16))
                for k, crop in crops.items():
                    w, h = crop.size
                    if w == 3:  # widen by repeating the last column
                        wide = Image.new("RGBA", (4, h))
                        wide.paste(crop, (0, 0))
                        wide.paste(crop.crop((2, 0, 3, h)), (3, 0))
                        crop = wide
                    im.paste(crop, regions[k][1])
        im.save(out / f"skin_{src.stem}.png")
        print(f"  skin {src.stem} ({'slim -> classic' if slim else 'classic'})")


def build_selection() -> None:
    """Create public/mc/*.png (names the kit loads) from the extracted game textures."""
    from PIL import Image
    tex = PUBLIC / "mc_assets" / "assets" / "minecraft" / "textures"
    out = PUBLIC / "mc"
    out.mkdir(parents=True, exist_ok=True)
    op = lambda rel: Image.open(tex / f"{rel}.png")
    tint(op("block/grass_block_top"), GRASS_TINT).save(out / "grass_top.png")
    side = op("block/grass_block_side").convert("RGBA")
    side.alpha_composite(tint(op("block/grass_block_side_overlay"), GRASS_TINT))
    side.save(out / "grass_side.png")
    tint(op("block/oak_leaves"), FOLIAGE_TINT).save(out / "leaves.png")
    tint(op("block/grass"), GRASS_TINT).save(out / "plant_grass.png")
    for n in PLANT_COPY:
        shutil.copy(tex / f"block/{n}.png", out / f"plant_{n}.png")
    for n in BLOCKS_COPY:
        shutil.copy(tex / f"block/{n}.png", out / f"{n}.png")
    shutil.copy(tex / "block/oak_door_bottom.png", out / "door_oak_lower.png")
    shutil.copy(tex / "block/oak_door_top.png", out / "door_oak_upper.png")
    water = op("block/water_still").convert("RGBA")
    alpha = water.getchannel("A")
    gray = water.convert("L").convert("RGBA")  # the game tints a grey texture with the biome colour: drop its own hue first
    gray.putalpha(alpha)
    tint(gray, WATER_TINT).save(out / "water_still.png")  # 16x512 animated strip, biome-tinted
    for n in ITEMS:
        shutil.copy(tex / f"item/{n}.png", out / f"item_{n}.png")
    for i in range(10):
        shutil.copy(tex / f"block/destroy_stage_{i}.png", out / f"destroy_{i}.png")
    fa_chest = PUBLIC / "mc_packs" / "fa_objects" / "assets" / "minecraft" / "textures" / "entity" / "chest" / "normal.png"
    shutil.copy(fa_chest if fa_chest.exists() else tex / "entity/chest/normal.png", out / "chest.png")
    shutil.copy(tex / "entity/signs/oak.png", out / "sign.png")
    shutil.copy(tex / "gui/widgets.png", out / "widgets.png")
    shutil.copy(tex / "gui/icons.png", out / "icons.png")
    shutil.copy(tex / "environment/clouds.png", out / "clouds.png")
    for name, rel in MOBS.items():
        shutil.copy(tex / f"{rel}.png", out / f"{name}.png")
    planks = op("block/oak_planks").convert("RGBA")
    empty = planks.copy()
    for (x0, y0, x1, y1) in ((1, 1, 15, 7), (1, 9, 15, 15)):
        for y in range(y0, y1):
            for x in range(x0, x1):
                shade = 38 - (y - y0) * 3
                empty.putpixel((x, y), (shade + 18, shade + 8, shade, 255))
    empty.save(out / "bookshelf_empty.png")
    base = op("entity/villager/villager").convert("RGBA")  # villager = base texture + profession layer (hat and robe)
    for prof in PROFESSIONS:
        v = base.copy()
        v.alpha_composite(op(f"entity/villager/profession/{prof}").convert("RGBA"))
        v.save(out / f"mob_villager_{prof}.png")
    for n in PLAYER_SKINS:
        shutil.copy(tex / f"entity/player/wide/{n}.png", out / f"skin_{n}.png")
    import_extra_skins(out)
    if not (out / "skin.png").exists():  # the user's own skin stays; default to Steve
        shutil.copy(tex / "entity/player/wide/steve.png", out / "skin.png")
    print(f"  selection written -> {out.relative_to(ROOT)}")


def build_sound_catalogue(ffmpeg_dir: Path) -> None:
    """public/mc/sound_events.json (event -> files) and normalised footstep copies in public/mc/sfx/."""
    import os
    import struct
    import subprocess
    import tempfile
    import wave
    snd = PUBLIC / "mc_sounds" / "minecraft"
    events = json.loads((snd / "sounds.json").read_text())
    cat = {}
    for ev, body in events.items():
        files = [(x["name"] if isinstance(x, dict) else x).replace("minecraft:", "") for x in body.get("sounds", [])]
        if files:
            cat[ev] = files
    (PUBLIC / "mc" / "sound_events.json").write_text(json.dumps(cat))
    print(f"  sound_events.json: {len(cat)} events")
    ff = ffmpeg_dir / "ffmpeg"
    if not ff.exists():
        print("!! ffmpeg not found, footstep boost skipped", file=sys.stderr)
        return
    env = dict(os.environ, DYLD_LIBRARY_PATH=str(ffmpeg_dir), LD_LIBRARY_PATH=str(ffmpeg_dir))
    sfx = PUBLIC / "mc" / "sfx"
    sfx.mkdir(parents=True, exist_ok=True)
    n = 0
    for ev, files in cat.items():
        # vanilla footsteps are far quieter than hits and breaks (grass peaks at 0.02): store normalised copies
        if not (re.fullmatch(r"block\.[a-z_]+\.step", ev) or re.fullmatch(r"entity\.(pig|cow|chicken|zombie|skeleton|player|sheep|spider)\.step", ev)):
            continue
        for k, f in enumerate(files, 1):
            src = snd / "sounds" / f"{f}.ogg"
            if not src.exists():
                continue
            with tempfile.NamedTemporaryFile(suffix=".wav") as t:
                subprocess.run([str(ff), "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", t.name], check=True, env=env)
                w = wave.open(t.name)
                frames = w.getnframes()
                d = struct.unpack(f"<{frames}h", w.readframes(frames))
            peak = max(abs(x) for x in d) or 1
            g = 0.9 * 32767 / peak
            o = wave.open(str(sfx / f"{ev.replace('.', '_')}_{k}.wav"), "wb")
            o.setnchannels(1); o.setsampwidth(2); o.setframerate(44100)
            o.writeframes(struct.pack(f"<{frames}h", *[max(-32768, min(32767, int(x * g))) for x in d]))
            o.close()
            n += 1
    print(f"  normalised footsteps: {n} files -> {sfx.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", type=Path, default=DEFAULT_JAR)
    ap.add_argument("--ffmpeg-dir", type=Path, default=ROOT / "remotion_studio" / "node_modules" / "@remotion" / "compositor-darwin-arm64")
    ap.add_argument("--assets-dir", type=Path, default=DEFAULT_ASSETS)
    ap.add_argument("--asset-index", default=DEFAULT_INDEX)
    ap.add_argument("--pack", type=Path, action="append", help="extra pack zip (extracted under mc_packs/<zip name>)")
    args = ap.parse_args()

    assets = PUBLIC / "mc_assets"
    if args.jar.exists():
        print(f"game jar: {args.jar}")
        print(f"  extracted {extract_jar(args.jar, assets)} files -> {assets.relative_to(ROOT)}")
        build_index(assets)
    else:
        print(f"!! game jar not found: {args.jar}", file=sys.stderr)

    if (args.assets_dir / "indexes" / f"{args.asset_index}.json").exists():
        sounds = PUBLIC / "mc_sounds"
        print(f"sounds: {args.assets_dir}")
        print(f"  extracted {extract_sounds(args.assets_dir, args.asset_index, sounds)} files -> {sounds.relative_to(ROOT)}")
    else:
        print(f"!! asset index not found in {args.assets_dir}", file=sys.stderr)

    packs = dict(DEFAULT_PACKS)
    for extra in args.pack or []:
        packs[re.sub(r"[^A-Za-z0-9]+", "_", extra.stem).lower()] = extra
    for name, zp in packs.items():
        if not zp.exists():
            print(f"!! pack not found, skipped: {zp}", file=sys.stderr)
            continue
        out = PUBLIC / "mc_packs" / name
        if out.exists():
            shutil.rmtree(out)
        print(f"pack {name}: extracted {extract_pack(zp, out)} files -> {out.relative_to(ROOT)}")
    print("processed selection:")
    build_selection()
    if (PUBLIC / "mc_sounds" / "minecraft" / "sounds.json").exists():
        build_sound_catalogue(args.ffmpeg_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
