#!/usr/bin/env python3
"""Describes every game screenshot / clip without a caption using a vision model (Gemini, or Cloudflare vision as fallback).
Captions are what lets a video show footage that matches what the narration says.   python scripts/caption_game_media.py [--limit 200]
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.game_images import available_games, caption_pending  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=200)
n = caption_pending(ap.parse_args().limit)
print(f"Captioned {n} item(s). Games ready to use: {available_games(include_blacklisted=True)}")
