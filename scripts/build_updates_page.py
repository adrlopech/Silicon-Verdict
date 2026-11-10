#!/usr/bin/env python3
"""Builds docs/changelog.html: every push to main with its full message, newest first, from `git log`.
Run it after a push (python scripts/build_updates_page.py) and commit the page; the portal's 'What's new' keeps only the three latest highlights."""
import html
import re
import subprocess
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REPO = "https://github.com/adrlopech/Silicon-Verdict/commit/"
SEP = "\x1e"


def commits():
    out = subprocess.run(["git", "log", "--no-merges", f"--format=%h{SEP}%ad{SEP}%an{SEP}%s{SEP}%b{SEP}END", "--date=short"], cwd=BASE, capture_output=True, text=True, check=True).stdout
    for chunk in out.split(f"{SEP}END"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        h, d, a, subj, body = (chunk.split(SEP) + [""] * 5)[:5]
        body = "\n".join(l for l in body.splitlines() if not l.startswith("Co-Authored-By"))
        yield h, d, subj, body.strip()


def kind(subj):
    m = re.match(r"(\w+)(?:\(([^)]*)\))?:\s*(.*)", subj)
    return (m.group(1), m.group(2) or "", m.group(3)) if m else ("update", "", subj)


def paras(body):
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in re.split(r"\n\s*\n", body) if p.strip())


def main():
    days = OrderedDict()
    for h, d, subj, body in commits():
        days.setdefault(d, []).append((h, subj, body))
    n = sum(len(v) for v in days.values())
    sections = ""
    for d, items in days.items():
        label = datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")
        rows = ""
        for h, subj, body in items:
            k, scope, text = kind(subj)
            rows += (f'<article class="up rv"><div class="up-top"><span class="up-k">{html.escape(k)}</span>'
                     f'{f"<span class=up-s>{html.escape(scope)}</span>" if scope else ""}'
                     f'<a class="up-h" href="{REPO}{h}" target="_blank" rel="noopener">{h}</a></div>'
                     f'<h3>{html.escape(text)}</h3>{paras(body)}</article>')
        sections += f'<section class="updays"><h2 class="up-day">{label}<small>{len(items)} update{"s" if len(items) != 1 else ""}</small></h2>{rows}</section>'
    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Every update — Silicon Verdict</title>
  <meta name="description" content="Every push to the Silicon Verdict project, in detail, newest first.">
  <meta name="theme-color" content="#05070C">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="apple-touch-icon.png">
  <link rel="stylesheet" href="style.css">
  <link rel="stylesheet" href="looks.css">
  <link rel="stylesheet" href="fixes.css">
  <link rel="stylesheet" href="premium.css">
  <link rel="stylesheet" href="rework.css">
  <script src="looks.js"></script>
</head>
<body>
  <div id="progress"></div>
  <div class="bg"><div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div></div>
  <header class="pill-wrap">
    <nav class="navpill" aria-label="Main">
      <a href="index.html#top" class="brand"><img src="logo.svg" alt="" width="40" height="40"><span>Silicon<b>Verdict</b></span></a>
      <ul class="pill-links">
        <li><a href="index.html#pipeline">Pipeline</a></li><li><a href="index.html#series">Series</a></li><li><a href="index.html#games">Content</a></li><li><a href="index.html#brand">Brand</a></li>
      </ul>
      <button class="cmdk" type="button" data-cmdk aria-label="Open the jump menu" aria-haspopup="dialog"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg><span>Jump to…</span><kbd>⌘K</kbd></button>
      <a class="cta-pill" href="https://www.youtube.com/@SiliconVerdictHQ" target="_blank" rel="noopener">Watch</a>
    </nav>
  </header>
  <main class="container">
    <section class="hero">
      <span class="tile lg" aria-hidden="true"><span class="ui" style="--i:url(assets/icons/ui-sparkles.svg)"></span></span>
      <h1>Every <span class="grad">update</span></h1>
      <p class="lead">{n} changes pushed to the project, newest first, each with the full note written when it was made.</p>
      <div class="btns"><a class="btn btn-s" href="index.html#changelog">&larr; Back to the portal</a></div>
    </section>
    {sections}
  </main>
  <footer>
    <div class="container foot">
      <div>&copy; 2026 Silicon Verdict. All rights reserved.<br><small>Independent hardware benchmark &amp; microarchitecture analysis pipeline.</small></div>
      <ul>
        <li><a href="index.html">Portal</a></li>
        <li><a href="terms.html">Terms of Service</a></li>
        <li><a href="privacy.html">Privacy Policy</a></li>
        <li><a href="mailto:imnotchego@gmail.com">Contact</a></li>
      </ul>
    </div>
  </footer>
  <script src="site.js"></script>
  <script src="nav.js"></script>
  <script src="premium.js" defer></script>
</body>
</html>
'''
    (BASE / "docs" / "changelog.html").write_text(page, encoding="utf-8")
    print(f"docs/changelog.html: {n} updates in {len(days)} days")


if __name__ == "__main__":
    main()
