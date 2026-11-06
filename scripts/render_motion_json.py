#!/usr/bin/env python3
"""Renders a ready-made MotionProject JSON (docs/generated_scripts/*.json) through the normal Motion Graphics pipeline, skipping the LLM.
Usage: python scripts/render_motion_json.py docs/generated_scripts/c1_ssd_myths.json
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import services.motion_generator as mg  # noqa: E402
from services.motion_generator import MotionProject  # noqa: E402
from services.motion_pipeline import run_motion_pipeline  # noqa: E402

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
project = MotionProject.model_validate(data)
mg.generate_motion_project = lambda *a, **k: project
res = run_motion_pipeline(topic=project.topic, fmt=project.format if project.format in mg.FORMATS else "auto", kind="curiosity", export_only=True)  # a topic skips the story bank, so the file is what gets rendered
print(json.dumps(res, indent=1))
