# Skins from NameMC

Downloaded on 2026-11-05 from the NameMC skin catalog (https://namemc.com/minecraft-skins), raw texture URL `https://s.namemc.com/i/<id>.png`.
Skins are creations of NameMC users: check their terms before using them in monetised videos.

| file | NameMC skin | model |
|---|---|---|
| tuxduck.png | https://namemc.com/skin/0778b4d4fef1d020 | slim (converted to classic arms for the kit) |
| shadow.png | https://namemc.com/skin/5c569957e3fb46cf | slim |
| duck.png | https://namemc.com/skin/7e46a0b5f8660b1e | classic |
| smiley.png | https://namemc.com/skin/8448b0e3d8167993 | slim |
| potato.png | https://namemc.com/skin/b9bf73d70dbd4744 | classic |
| goth.png | https://namemc.com/skin/cfb5af4dd4b7b07a | slim |

`scripts/extract_minecraft_assets.py` (`import_extra_skins`) copies them to `remotion_studio/public/mc/skin_<file>.png`, widening slim arms to the 4 px arms the kit's player model uses.
