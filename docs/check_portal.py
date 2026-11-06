"""Checks that every local link, script, stylesheet and #anchor in docs/*.html exists. Run: python3 docs/check_portal.py"""
import re
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
bad = []
for page in sorted(D.glob("*.html")):
    if page.name.startswith("tiktok-developers"):
        continue
    html = page.read_text(encoding="utf-8")
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    for url in re.findall(r'(?:href|src)="([^"]+)"', html):
        if url.startswith(("http", "mailto:", "data:", "//")):
            continue
        path, _, frag = url.partition("#")
        if path and not (D / path).exists():
            bad.append(f"{page.name}: missing file {url}")
        if frag and not path and frag not in ids:
            bad.append(f"{page.name}: missing anchor #{frag}")
        if frag and path and path.endswith(".html") and (D / path).exists():
            if frag not in set(re.findall(r'\bid="([^"]+)"', (D / path).read_text(encoding="utf-8"))):
                bad.append(f"{page.name}: missing anchor {url}")
print("\n".join(bad) or "portal links OK")
sys.exit(1 if bad else 0)
