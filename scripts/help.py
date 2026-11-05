#!/usr/bin/env python3
"""Silicon Verdict Command Center & System Help Guide.

Lists all configured chat triggers, interactive options, CLI scripts, and directory structures.
"""

HELP_TEXT = """================================================================================
 ⚡ SILICON VERDICT: COMMAND CENTER & OPERATIONAL PIPELINE MANUAL
================================================================================

1. PRIMARY CHAT COMMANDS (Direct Text Triggers)
--------------------------------------------------------------------------------
 • genera
   Triggers the two-step interactive production workflow:
   1. Pauses automatic generation and prompts with thematic selection [1, 2, 3, or 4].
   2. Upon receiving your selection, produces a unified vertical master (60-120s),
      enforces word budget guardrails (145-260w), high-CTR Frame 0 cover, semantic
      B-roll, auto-publishes to YouTube Shorts, and generates local staging files
      in output/tiktok/ for seamless manual upload.

 • corregir
   On-demand QA and automated audit system (does NOT run automatically):
   1. Audits latest video in output/tiktok/: subtitles/Whisper, audio clipping,
      B-roll coherence, mobile Safe Zones, and cover frame.
   2. Outputs comprehensive audit report and asks for user confirmation ("Yes" / "No").
   3. If confirmed, rebuilds corrected video and saves rules in data/qa_rules.json.

 • limpieza
   Atomic disk cleanup:
   - Purges every per-video folder in output/tiktok/ (video, cover and metadata).
   - Purges every per-video folder in output/youtube/.
   - Purges intermediate render frames and cache folders in temp/.
   - PRESERVES intact: data/history.db, credentials (.env), tokens, and assets/broll/.

 • help / commands
   Displays this detailed command reference, CLI syntax, and architecture guide.

--------------------------------------------------------------------------------
2. INTERACTIVE "genera" MENU OPTIONS
--------------------------------------------------------------------------------
 [1] Hardware Deep Dive & Benchmarks
     Remotion Kinetic 60 FPS: Silicon compute dies, L3 cache bonding, memory buses,
     latency telemetry bars, and 1% low frame pacing tachometer.

 [2] Gaming & Optimization
     Remotion Kinetic 60 FPS: PresentMon frametimes, competitive preset cards,
     DLSS vs Native pacing stability, and 99th percentile micro-stutter analysis.

 [3] Tech Curiosities & Storytelling
     Remotion Kinetic 60 FPS: Applied physics, 2.45 GHz RF collision waveforms,
     abyssal subsea fiber cables, GPS relativistic time dilation, and VCSEL arrays.

 [4] Automatic (AI)
     Queries data/history.db to select the optimal category based on rotation rest
     periods and audience retention analytics.

--------------------------------------------------------------------------------
3. TERMINAL COMMANDS & CLI (Headless Execution & Maintenance)
--------------------------------------------------------------------------------
 • Direct production via CLI:
   .venv/bin/python main.py --category 1 --privacy public     # Hardware Benchmarks
   .venv/bin/python main.py --category 2 --privacy public     # Gaming & Optimization
   .venv/bin/python main.py --category 3 --privacy public     # Tech Curiosities
   .venv/bin/python main.py --category auto --privacy public  # Auto AI rotation

 • Interactive terminal mode:
   .venv/bin/python main.py --interactive

 • QA audit and correction via CLI:
   .venv/bin/python main.py --audit-latest                   # Report only
   .venv/bin/python main.py --apply-fixes                    # Apply corrections

 • Scheduler and automated jobs:
   .venv/bin/python scripts/scheduler.py --run-now           # Today's production
   .venv/bin/python scripts/cleanup.py                       # Disk cleanup

 • MLOps, B-Roll, and Analytics:
   .venv/bin/python scripts/index_broll.py                   # Auto-index new B-roll
   .venv/bin/python scripts/analytics_sync.py                # Sync YouTube Analytics
   .venv/bin/python scripts/analytics_sync.py --simulate     # Offline analytics simulation
   .venv/bin/python scripts/authenticate_yt.py               # Authorize OAuth credentials

--------------------------------------------------------------------------------
4. KEY DIRECTORIES & FILES
--------------------------------------------------------------------------------
 • output/youtube/<title>/ One folder per video (named after its title); video named by date and time.
 • output/tiktok/<title>/  One folder per video with <date_time>.mp4, _cover.jpg and .txt metadata.
 • data/history.db        SQLite database: 30-topic queue, telemetry, and API costs.
 • data/category_weights.json  Dynamic algorithmic weights driven by real audience retention.
 • data/qa_rules.json     Learned phonetic pronunciation rules and hook filters.
 • assets/broll/          Permanent background video library and manifest.json.
================================================================================
"""

def print_help() -> None:
    """Prints the Silicon Verdict command center help guide."""
    print(HELP_TEXT)


if __name__ == "__main__":
    print_help()
