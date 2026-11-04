#!/usr/bin/env python3
"""
demo_server.py - Silicon Verdict Pipeline Dashboard (Local Demo Server)
Simulates TikTok Login Kit and Content Posting API integrations for developer review.
Serves a high-fidelity dark/glassmorphic web UI on http://localhost:8080.
"""

import os
import sys
import json
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

PORT = 8080
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_VIDEO_PATH = BASE_DIR / "temp" / "test_liquid_glass_vertical.mp4"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1920, height=1080, initial-scale=1.0">
  <title>Silicon Verdict // Pipeline Automation & TikTok Posting Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #07090e;
      --bg-card: rgba(15, 23, 42, 0.75);
      --bg-card-border: rgba(255, 255, 255, 0.1);
      --primary-cyan: #00f2fe;
      --primary-emerald: #10b981;
      --tiktok-pink: #fe2c55;
      --tiktok-cyan: #25f4ee;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-glow: rgba(0, 242, 254, 0.15);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
    }

    body {
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 85% 85%, rgba(254, 44, 85, 0.07) 0%, transparent 45%),
        radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.04) 0%, transparent 55%);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      height: 1080px;
      width: 1920px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Virtual Mouse Cursor */
    #virtual-cursor {
      position: fixed;
      width: 22px;
      height: 22px;
      border: 2px solid #ffffff;
      background: rgba(0, 242, 254, 0.8);
      border-radius: 50%;
      pointer-events: none;
      z-index: 999999;
      transform: translate(-50%, -50%);
      box-shadow: 0 0 15px #00f2fe, 0 0 30px rgba(0, 242, 254, 0.6);
      transition: width 0.15s, height 0.15s, background-color 0.15s;
    }
    #virtual-cursor.clicking {
      width: 32px;
      height: 32px;
      background: rgba(254, 44, 85, 0.9);
      box-shadow: 0 0 25px #fe2c55;
    }

    /* Header Bar */
    header {
      height: 72px;
      padding: 0 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--bg-card-border);
      background: rgba(10, 15, 29, 0.85);
      backdrop-filter: blur(20px);
      z-index: 100;
    }

    .brand-wrap {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .brand-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, var(--primary-cyan), #3b82f6);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 20px rgba(0, 242, 254, 0.4);
    }
    .brand-icon svg {
      width: 24px;
      height: 24px;
      fill: #030712;
    }
    .brand-title {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-badge {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(0, 242, 254, 0.15);
      color: var(--primary-cyan);
      border: 1px solid rgba(0, 242, 254, 0.3);
    }
    .brand-sub {
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 500;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 20px;
    }
    .sys-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--bg-card-border);
      font-size: 13px;
      color: var(--text-muted);
    }
    .dot-status {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #eab308;
      box-shadow: 0 0 10px #eab308;
    }
    .dot-status.connected {
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
    }

    /* Main Container */
    main {
      flex: 1;
      padding: 32px 40px;
      display: grid;
      grid-template-columns: 460px 1fr;
      gap: 36px;
      height: calc(1080px - 72px);
      overflow: hidden;
    }

    /* Glass Cards */
    .glass-card {
      background: var(--bg-card);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--bg-card-border);
      border-radius: 20px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
      position: relative;
      overflow: hidden;
    }
    .glass-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    }

    /* Left Column: Phone / Video Preview */
    .preview-col {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .phone-container {
      background: #000;
      border-radius: 28px;
      border: 4px solid #1e293b;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 35px rgba(0, 242, 254, 0.15);
      position: relative;
      height: 760px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .phone-notch {
      position: absolute;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      width: 120px;
      height: 22px;
      background: #0f172a;
      border-radius: 12px;
      z-index: 20;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .phone-notch-cam {
      width: 8px;
      height: 8px;
      background: #1e293b;
      border-radius: 50%;
    }
    .video-frame {
      width: 100%;
      height: 100%;
      position: relative;
      background: #020617;
    }
    #preview-video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .safe-zone-overlay {
      position: absolute;
      top: 60px;
      bottom: 120px;
      left: 24px;
      right: 64px;
      border: 1.5px dashed rgba(0, 242, 254, 0.4);
      border-radius: 8px;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 10px;
      background: rgba(0, 242, 254, 0.02);
    }
    .safe-zone-badge {
      align-self: flex-start;
      font-size: 10px;
      font-weight: 700;
      color: var(--primary-cyan);
      background: rgba(0, 0, 0, 0.6);
      padding: 3px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
    }
    .video-telemetry-badge {
      position: absolute;
      bottom: 16px;
      left: 16px;
      right: 16px;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
      z-index: 10;
    }

    .clip-meta-card {
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .clip-title-label {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
    }
    .clip-sub-label {
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      gap: 12px;
    }

    /* Right Column: Dashboard Controls */
    .controls-col {
      display: flex;
      flex-direction: column;
      gap: 20px;
      height: 100%;
    }

    /* Section 1: TikTok Auth Status Card */
    .auth-banner-card {
      padding: 24px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      border-left: 4px solid #fe2c55;
    }
    .auth-banner-card.connected {
      border-left-color: #10b981;
    }
    .tiktok-logo-badge {
      width: 52px;
      height: 52px;
      border-radius: 14px;
      background: #000;
      border: 1px solid rgba(255, 255, 255, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: -2px -2px 10px rgba(37, 244, 238, 0.3), 2px 2px 10px rgba(254, 44, 85, 0.3);
      flex-shrink: 0;
    }
    .tiktok-logo-badge svg {
      width: 28px;
      height: 28px;
      fill: #fff;
    }
    .auth-info-wrap {
      flex: 1;
    }
    .auth-state-header {
      font-size: 17px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 4px;
    }
    .auth-state-desc {
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.4;
    }
    .scope-tags {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    .scope-tag {
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      color: #cbd5e1;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .scope-tag.active {
      background: rgba(16, 185, 129, 0.12);
      color: #34d399;
      border-color: rgba(16, 185, 129, 0.3);
    }

    /* TikTok Connect Button */
    .btn-tiktok-connect {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #000;
      color: #fff;
      border: 1.5px solid rgba(255, 255, 255, 0.2);
      border-radius: 12px;
      padding: 14px 26px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5), -2px -2px 12px rgba(37, 244, 238, 0.2), 2px 2px 12px rgba(254, 44, 85, 0.2);
      transition: all 0.2s ease;
      white-space: nowrap;
    }
    .btn-tiktok-connect:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), -3px -3px 18px rgba(37, 244, 238, 0.4), 3px 3px 18px rgba(254, 44, 85, 0.4);
    }

    /* Section 2: Posting Parameters Card */
    .posting-config-card {
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .config-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
    }
    .input-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .input-label {
      font-size: 13px;
      font-weight: 600;
      color: #cbd5e1;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .text-input, .select-input {
      background: rgba(10, 15, 29, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 12px 16px;
      font-size: 14px;
      color: #fff;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .text-input:focus, .select-input:focus {
      border-color: var(--primary-cyan);
      box-shadow: 0 0 15px rgba(0, 242, 254, 0.2);
    }
    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 24px;
      margin-top: 2px;
    }
    .checkbox-item {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      color: #94a3b8;
    }
    .custom-check {
      width: 18px;
      height: 18px;
      border-radius: 5px;
      background: rgba(0, 242, 254, 0.15);
      border: 1.5px solid var(--primary-cyan);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--primary-cyan);
      font-size: 12px;
      font-weight: bold;
    }

    /* Primary Action Button: Publish to TikTok */
    .publish-bar-wrap {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      margin-top: 4px;
    }
    .btn-publish-tiktok {
      background: linear-gradient(135deg, #00f2fe 0%, #3b82f6 50%, #fe2c55 100%);
      color: #ffffff;
      border: none;
      border-radius: 12px;
      padding: 14px 34px;
      font-size: 15px;
      font-weight: 800;
      letter-spacing: 0.3px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: 0 6px 25px rgba(0, 242, 254, 0.35);
      transition: all 0.2s ease;
    }
    .btn-publish-tiktok:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 10px 35px rgba(0, 242, 254, 0.55);
    }
    .btn-publish-tiktok:disabled {
      opacity: 0.45;
      cursor: not-allowed;
      filter: grayscale(0.5);
    }

    /* Section 3: Telemetry & Console Card */
    .telemetry-card {
      flex: 1;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: rgba(7, 10, 18, 0.9);
    }
    .telemetry-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .traffic-lights {
      display: flex;
      gap: 6px;
    }
    .traffic-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .dot-red { background: #ef4444; }
    .dot-yellow { background: #f59e0b; }
    .dot-green { background: #10b981; }
    .telemetry-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 1px;
      text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
    }

    /* Upload Progress Bar */
    .progress-section {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .progress-labels {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      color: #94a3b8;
    }
    .progress-track {
      height: 8px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      overflow: hidden;
      position: relative;
    }
    .progress-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #25f4ee, #00f2fe, #fe2c55);
      border-radius: 4px;
      transition: width 0.3s ease;
      box-shadow: 0 0 12px rgba(0, 242, 254, 0.6);
    }

    /* Console Terminal Window */
    .console-logs {
      flex: 1;
      background: #020408;
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 10px;
      padding: 14px 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      line-height: 1.6;
      color: #94a3b8;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .log-line {
      display: flex;
      gap: 12px;
    }
    .log-time {
      color: #64748b;
      flex-shrink: 0;
    }
    .log-method {
      font-weight: 700;
      flex-shrink: 0;
    }
    .log-method.post { color: #38bdf8; }
    .log-method.put { color: #f59e0b; }
    .log-method.ok { color: #10b981; }
    .log-text {
      color: #e2e8f0;
      word-break: break-all;
    }

    /* Success Card Notification */
    .success-alert {
      display: none;
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 78, 59, 0.4));
      border: 1.5px solid #10b981;
      border-radius: 12px;
      padding: 12px 18px;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 0 25px rgba(16, 185, 129, 0.25);
      animation: fadeIn 0.4s ease forwards;
    }
    .success-alert.show {
      display: flex;
    }
    .success-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .success-icon {
      width: 32px;
      height: 32px;
      background: #10b981;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #000;
      font-weight: 800;
      font-size: 16px;
    }
    .success-title {
      font-size: 14px;
      font-weight: 700;
      color: #34d399;
    }
    .success-sub {
      font-size: 12px;
      color: #cbd5e1;
      font-family: 'JetBrains Mono', monospace;
    }

    /* TikTok OAuth Modal Overlay */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(3, 7, 18, 0.75);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
    }
    .modal-overlay.active {
      display: flex;
      animation: fadeIn 0.3s ease;
    }

    .oauth-window {
      width: 580px;
      background: #0f172a;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 24px;
      box-shadow: 0 30px 80px rgba(0, 0, 0, 0.8), 0 0 40px rgba(37, 244, 238, 0.2);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .oauth-header {
      background: #020617;
      padding: 22px 28px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .oauth-brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .oauth-body {
      padding: 28px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      max-height: 520px;
      overflow-y: auto;
    }
    .oauth-app-card {
      display: flex;
      align-items: center;
      gap: 16px;
      background: rgba(255, 255, 255, 0.03);
      padding: 16px;
      border-radius: 14px;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .oauth-app-icon {
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #00f2fe, #3b82f6);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .oauth-scope-item {
      display: flex;
      gap: 16px;
      padding: 14px 16px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      transition: border-color 0.2s, background 0.2s;
    }
    .oauth-scope-item:hover {
      border-color: rgba(0, 242, 254, 0.3);
      background: rgba(0, 242, 254, 0.03);
    }
    .scope-num-badge {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: rgba(37, 244, 238, 0.15);
      color: var(--primary-cyan);
      border: 1px solid rgba(37, 244, 238, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      flex-shrink: 0;
    }
    .scope-detail-title {
      font-size: 14px;
      font-weight: 700;
      color: #f1f5f9;
      margin-bottom: 2px;
    }
    .scope-tech-name {
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      display: inline-block;
      padding: 1px 6px;
      border-radius: 4px;
      margin-bottom: 4px;
    }
    .scope-desc {
      font-size: 12px;
      color: #94a3b8;
      line-height: 1.4;
    }

    .oauth-footer {
      padding: 20px 28px;
      background: #020617;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .btn-oauth-cancel {
      background: transparent;
      color: #94a3b8;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 10px 20px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-oauth-grant {
      background: linear-gradient(135deg, #fe2c55, #ff0050);
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 12px 26px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 4px 18px rgba(254, 44, 85, 0.4);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn-oauth-grant:hover {
      box-shadow: 0 6px 24px rgba(254, 44, 85, 0.6);
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>

  <!-- Virtual Pointer -->
  <div id="virtual-cursor" style="top: 200px; left: 500px;"></div>

  <!-- Header -->
  <header>
    <div class="brand-wrap">
      <div class="brand-icon">
        <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
      </div>
      <div>
        <div class="brand-title">
          SILICON VERDICT
          <span class="brand-badge">PIPELINE STUDIO</span>
        </div>
        <div class="brand-sub">Automated GPU/CPU Benchmark Synthesis & TikTok Publisher</div>
      </div>
    </div>
    <div class="header-actions">
      <div class="sys-pill">
        <span>Render Engine:</span>
        <strong style="color: #38bdf8;">v2.4 Liquid Glass</strong>
      </div>
      <div class="sys-pill" id="header-auth-pill">
        <div class="dot-status" id="header-dot"></div>
        <span id="header-auth-status">TikTok: Not Connected</span>
      </div>
    </div>
  </header>

  <!-- Main Grid -->
  <main>
    <!-- Left Column: Video Preview & Specs (View 2) -->
    <div class="preview-col">
      <div class="phone-container">
        <div class="phone-notch">
          <div class="phone-notch-cam"></div>
        </div>
        <div class="video-frame">
          <video id="preview-video" src="/video/sample.mp4" loop muted playsinline></video>
          
          <!-- Safe Zone Overlay Grid -->
          <div class="safe-zone-overlay" id="safe-zone-overlay">
            <span class="safe-zone-badge">SAFE ZONE: 1080x1920 (ACTIVE)</span>
            <div style="font-size: 10px; color: rgba(255,255,255,0.4); text-align: right; font-family: monospace;">
              TITLES & CTA AREA COMPLIANT
            </div>
          </div>

          <!-- Video Specs Badge -->
          <div class="video-telemetry-badge">
            <span>1080x1920 • 60 FPS • 14.2 Mbps</span>
            <span style="color: #10b981;">EBU R128 PASS</span>
          </div>
        </div>
      </div>

      <div class="glass-card clip-meta-card">
        <div class="clip-title-label">Active Clip: PCIe 4.0 vs 5.0 Throughput Benchmark</div>
        <div class="clip-sub-label">
          <span>Engine: Liquid Glass Zero-Collision</span>
          <span>Audio: Cyberpunk Dark Synth</span>
        </div>
      </div>
    </div>

    <!-- Right Column: Control Panel & Telemetry (View 1 & View 3) -->
    <div class="controls-col">

      <!-- View 1: TikTok Connection & Scopes Card -->
      <div class="glass-card auth-banner-card" id="auth-banner-card">
        <div class="tiktok-logo-badge">
          <!-- TikTok Official Logo SVG -->
          <svg viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 3 15.68 6.34 6.34 0 0 0 9.34 22a6.34 6.34 0 0 0 6.33-6.33V9.75a8.16 8.16 0 0 0 4.79 1.55v-3.4a4.85 4.85 0 0 1-.87-1.21z"/></svg>
        </div>

        <div class="auth-info-wrap" id="auth-info-wrap">
          <div class="auth-state-header" id="auth-state-header">
            <span>TikTok Integration: Login Kit Required</span>
          </div>
          <div class="auth-state-desc" id="auth-state-desc">
            Connect your TikTok account to authorize direct video publishing and status tracking via TikTok Login Kit and Content Posting API.
          </div>
          <div class="scope-tags">
            <span class="scope-tag" id="tag-scope-1">user.info.basic</span>
            <span class="scope-tag" id="tag-scope-2">video.upload</span>
            <span class="scope-tag" id="tag-scope-3">video.publish</span>
          </div>
        </div>

        <button class="btn-tiktok-connect" id="btn-connect-tiktok">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="#fff"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 3 15.68 6.34 6.34 0 0 0 9.34 22a6.34 6.34 0 0 0 6.33-6.33V9.75a8.16 8.16 0 0 0 4.79 1.55v-3.4a4.85 4.85 0 0 1-.87-1.21z"/></svg>
          Connect with TikTok
        </button>
      </div>

      <!-- View 2 & 3: Publishing Configuration Card -->
      <div class="glass-card posting-config-card">
        <div class="config-grid">
          <div class="input-group">
            <label class="input-label" for="video-title-input">
              <span>Video Title & Hashtags (Direct Publish)</span>
              <span style="font-size: 11px; color: #64748b;" id="char-counter">64 / 2200</span>
            </label>
            <input type="text" id="video-title-input" class="text-input" value="PCIe 4.0 vs 5.0: The Benchmark Truth #hardware #techtok">
          </div>
          <div class="input-group">
            <label class="input-label" for="privacy-select">Privacy Settings</label>
            <select id="privacy-select" class="select-input">
              <option value="PUBLIC_TO_EVERYONE" selected>Direct Publish (Public)</option>
              <option value="MUTUAL_FOLLOW_FRIENDS">Friends Only</option>
              <option value="SELF_ONLY">Private (Only Me)</option>
            </select>
          </div>
        </div>

        <div class="checkbox-row">
          <div class="checkbox-item">
            <div class="custom-check">✓</div>
            <span>Safe Zone Compliance Verified</span>
          </div>
          <div class="checkbox-item">
            <div class="custom-check">✓</div>
            <span>Original Sound Active (Stereo Mix)</span>
          </div>
          <div class="checkbox-item">
            <div class="custom-check">✓</div>
            <span>Commercial Disclosure: None</span>
          </div>
        </div>

        <div class="publish-bar-wrap">
          <div style="font-size: 12px; color: #64748b; font-family: 'JetBrains Mono', monospace;">
            Payload Status: READY • Direct API Dispatch Mode
          </div>
          <button class="btn-publish-tiktok" id="btn-publish-tiktok" disabled>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#fff"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 3 15.68 6.34 6.34 0 0 0 9.34 22a6.34 6.34 0 0 0 6.33-6.33V9.75a8.16 8.16 0 0 0 4.79 1.55v-3.4a4.85 4.85 0 0 1-.87-1.21z"/></svg>
            Publish to TikTok
          </button>
        </div>
      </div>

      <!-- View 3: Telemetry Console & Progress Bar -->
      <div class="glass-card telemetry-card">
        <div class="telemetry-header">
          <div class="traffic-lights">
            <div class="traffic-dot dot-red"></div>
            <div class="traffic-dot dot-yellow"></div>
            <div class="traffic-dot dot-green"></div>
          </div>
          <div class="telemetry-title">TikTok Content Posting API Telemetry Console</div>
          <div style="font-size: 11px; color: #64748b; font-family: monospace;">ENDPOINT: open.tiktokapis.com/v2</div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-section">
          <div class="progress-labels">
            <span id="upload-stage-label">Upload Channel: Idle</span>
            <span id="upload-percent-label">0% (0.00 MB / 1.25 MB)</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" id="progress-fill"></div>
          </div>
        </div>

        <!-- Real-Time Console Window -->
        <div class="console-logs" id="console-logs">
          <div class="log-line">
            <span class="log-time">[14:30:00.102]</span>
            <span class="log-text" style="color: #64748b;">// Silicon Verdict TikTok Gateway Ready. Waiting for user authentication...</span>
          </div>
        </div>

        <!-- Success Alert Badge -->
        <div class="success-alert" id="success-alert">
          <div class="success-left">
            <div class="success-icon">✓</div>
            <div>
              <div class="success-title">Video successfully published to TikTok!</div>
              <div class="success-sub">Publish ID: <span style="color:#38bdf8;">v_pub_7392019482</span> • Account: <span style="color:#fff;">@SiliconVerdict</span></div>
            </div>
          </div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #34d399; background: rgba(16, 185, 129, 0.2); padding: 4px 10px; border-radius: 6px;">
            PUBLISH_COMPLETE
          </div>
        </div>
      </div>

    </div>
  </main>

  <!-- TikTok OAuth Consent Screen Modal (View 1) -->
  <div class="modal-overlay" id="oauth-modal">
    <div class="oauth-window" id="oauth-window">
      <!-- Modal Header -->
      <div class="oauth-header">
        <div class="oauth-brand">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 3 15.68 6.34 6.34 0 0 0 9.34 22a6.34 6.34 0 0 0 6.33-6.33V9.75a8.16 8.16 0 0 0 4.79 1.55v-3.4a4.85 4.85 0 0 1-.87-1.21z"/></svg>
          <span style="font-size: 16px; font-weight: 700;">TikTok Login Kit</span>
        </div>
        <div style="font-size: 12px; color: #64748b;">OAuth 2.0 Consent Screen</div>
      </div>

      <!-- Modal Body -->
      <div class="oauth-body" id="oauth-body-scroll">
        <div class="oauth-app-card">
          <div class="oauth-app-icon">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="#030712"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          </div>
          <div>
            <div style="font-size: 15px; font-weight: 700; color: #fff;">Silicon Verdict Pipeline</div>
            <div style="font-size: 12px; color: #94a3b8;">is requesting permission to access your TikTok account:</div>
            <div style="font-size: 13px; font-weight: 700; color: #25f4ee; margin-top: 2px;">@SiliconVerdict (Creator Account)</div>
          </div>
        </div>

        <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.8px;">
          Requested Permissions (3 Scopes):
        </div>

        <!-- Scope 1 -->
        <div class="oauth-scope-item" id="scope-card-1">
          <div class="scope-num-badge">1</div>
          <div>
            <div class="scope-detail-title">Read profile username & avatar</div>
            <span class="scope-tech-name">user.info.basic</span>
            <div class="scope-desc">
              Allows Silicon Verdict to read your TikTok username and profile picture to verify account connectivity and display your identity in the pipeline dashboard.
            </div>
          </div>
        </div>

        <!-- Scope 2 -->
        <div class="oauth-scope-item" id="scope-card-2">
          <div class="scope-num-badge">2</div>
          <div>
            <div class="scope-detail-title">Upload video files to TikTok storage</div>
            <span class="scope-tech-name">video.upload</span>
            <div class="scope-desc">
              Allows the pipeline to stream rendered 1080x1920 Liquid Glass benchmark videos in binary chunks to TikTok cloud media servers.
            </div>
          </div>
        </div>

        <!-- Scope 3 -->
        <div class="oauth-scope-item" id="scope-card-3">
          <div class="scope-num-badge">3</div>
          <div>
            <div class="scope-detail-title">Publish videos directly to account</div>
            <span class="scope-tech-name">video.publish</span>
            <div class="scope-desc">
              Allows direct publishing of benchmark shorts to your TikTok feed with pre-configured title, safe zone metadata, and privacy controls.
            </div>
          </div>
        </div>

        <div style="font-size: 11px; color: #64748b; line-height: 1.4;">
          By authorizing, you grant Silicon Verdict permission to use these scopes according to the 
          <span style="color: #38bdf8;">Developer Terms of Service</span> and <span style="color: #38bdf8;">Privacy Policy</span>. 
          You can revoke these permissions anytime in TikTok Settings.
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="oauth-footer">
        <button class="btn-oauth-cancel" id="btn-modal-cancel">Cancel</button>
        <button class="btn-oauth-grant" id="btn-modal-authorize">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="#fff"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
          Authorize / Grant Permissions
        </button>
      </div>
    </div>
  </div>

  <script>
    // Elements
    const cursor = document.getElementById('virtual-cursor');
    const btnConnect = document.getElementById('btn-connect-tiktok');
    const modal = document.getElementById('oauth-modal');
    const btnAuthorize = document.getElementById('btn-modal-authorize');
    const btnCancel = document.getElementById('btn-modal-cancel');
    const previewVideo = document.getElementById('preview-video');
    const btnPublish = document.getElementById('btn-publish-tiktok');
    const consoleLogs = document.getElementById('console-logs');
    const progressFill = document.getElementById('progress-fill');
    const uploadPercentLabel = document.getElementById('upload-percent-label');
    const uploadStageLabel = document.getElementById('upload-stage-label');
    const successAlert = document.getElementById('success-alert');
    const headerDot = document.getElementById('header-dot');
    const headerAuthStatus = document.getElementById('header-auth-status');
    const authStateHeader = document.getElementById('auth-state-header');
    const authStateDesc = document.getElementById('auth-state-desc');
    const authBannerCard = document.getElementById('auth-banner-card');

    // Virtual cursor tracker
    window.addEventListener('mousemove', (e) => {
      cursor.style.left = e.clientX + 'px';
      cursor.style.top = e.clientY + 'px';
    });
    window.addEventListener('mousedown', () => cursor.classList.add('clicking'));
    window.addEventListener('mouseup', () => cursor.classList.remove('clicking'));

    function log(method, text, type = '') {
      const line = document.createElement('div');
      line.className = 'log-line';
      const now = new Date().toISOString().substring(11, 23);
      line.innerHTML = `
        <span class="log-time">[${now}]</span>
        ${method ? `<span class="log-method ${type}">${method}</span>` : ''}
        <span class="log-text">${text}</span>
      `;
      consoleLogs.appendChild(line);
      consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Modal Actions
    btnConnect.addEventListener('click', () => {
      modal.classList.add('active');
      log('INFO', 'TikTok Login Kit OAuth dialog opened. Presenting user consent view...');
    });

    btnCancel.addEventListener('click', () => {
      modal.classList.remove('active');
    });

    btnAuthorize.addEventListener('click', () => {
      modal.classList.remove('active');
      
      // Update UI to Connected State
      headerDot.classList.add('connected');
      headerAuthStatus.textContent = 'Account: @SiliconVerdict (Authenticated)';
      headerAuthStatus.style.color = '#34d399';

      authBannerCard.classList.add('connected');
      authStateHeader.innerHTML = '<span style="color:#34d399;">✓ Account Connected: @SiliconVerdict</span> <span style="font-size:12px; background:rgba(16,185,129,0.2); color:#34d399; padding:2px 8px; border-radius:12px;">Authenticated</span>';
      authStateDesc.innerHTML = 'Authorized via TikTok Login Kit OAuth 2.0. Scopes active: <strong>user.info.basic, video.upload, video.publish</strong>.';
      
      document.getElementById('tag-scope-1').classList.add('active');
      document.getElementById('tag-scope-2').classList.add('active');
      document.getElementById('tag-scope-3').classList.add('active');

      btnConnect.style.display = 'none';

      const connectedBadge = document.createElement('div');
      connectedBadge.style.cssText = 'display:flex; align-items:center; gap:8px; font-size:13px; font-weight:700; color:#34d399; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); padding:10px 18px; border-radius:10px;';
      connectedBadge.innerHTML = '<span>● Session Token Valid (24h)</span>';
      authBannerCard.appendChild(connectedBadge);

      btnPublish.disabled = false;

      log('OK', 'OAuth 2.0 Authorization Code exchange successful. Access token cached.', 'ok');
      log('INFO', 'TikTok Scopes Granted: [user.info.basic, video.upload, video.publish]');
    });

    // Content Posting Flow
    btnPublish.addEventListener('click', async () => {
      btnPublish.disabled = true;
      btnPublish.innerHTML = 'Publishing...';
      
      log('POST', '/v2/post/publish/video/init/ -> Initializing Content Posting API session...', 'post');
      uploadStageLabel.textContent = 'Step 1/3: Negotiating Upload Session';
      
      await new Promise(r => setTimeout(r, 1200));

      log('200 OK', 'Session Created: { publish_id: "v_pub_7392019482", upload_url: "https://open-api.tiktok.com/upload/v1/..." }', 'ok');
      uploadStageLabel.textContent = 'Step 2/3: Uploading Video Binary Chunks';
      log('PUT', '/v2/post/publish/video/upload/chunk_0 -> Streaming 1.25 MB binary payload...', 'put');

      // Animate Progress Bar
      let pct = 0;
      const interval = setInterval(() => {
        pct += 10;
        if (pct > 100) pct = 100;
        progressFill.style.width = pct + '%';
        const mb = ((1.25 * pct) / 100).toFixed(2);
        uploadPercentLabel.textContent = `${pct}% (${mb} MB / 1.25 MB)`;
        
        if (pct === 100) {
          clearInterval(interval);
          finishUpload();
        }
      }, 350);

      async function finishUpload() {
        log('200 OK', 'PUT Binary Upload: 100% completed. Checksum verification passed (SHA-256 match).', 'ok');
        uploadStageLabel.textContent = 'Step 3/3: TikTok Ingestion & Publishing Status Check';
        
        await new Promise(r => setTimeout(r, 1000));
        log('POST', '/v2/post/publish/status/fetch/ -> Querying publish_id: "v_pub_7392019482"', 'post');
        
        await new Promise(r => setTimeout(r, 1200));
        log('200 OK', 'Response: { status: "PUBLISH_COMPLETE", publish_id: "v_pub_7392019482", fail_reason: null }', 'ok');
        log('OK', '[SUCCESS] Video successfully published to TikTok Feed (@SiliconVerdict)!', 'ok');
        
        uploadStageLabel.textContent = 'Publishing Finished: Status 200 OK (PUBLISH_COMPLETE)';
        btnPublish.innerHTML = 'Published ✓';
        btnPublish.style.background = '#10b981';
        successAlert.classList.add('show');
      }
    });
  </script>
</body>
</html>
"""

class DemoRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep terminal output clean
        sys.stderr.write(f"[demo_server] {self.address_string()} - {format % args}\n")

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path in ["/", "/index.html"]:
            content = HTML_CONTENT.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == "/video/sample.mp4":
            if not SAMPLE_VIDEO_PATH.exists():
                self.send_error(404, "Sample video not found")
                return

            file_size = SAMPLE_VIDEO_PATH.stat().st_size
            range_header = self.headers.get("Range")

            if range_header:
                # Handle HTTP Range (bytes=start-end)
                byte_range = range_header.strip().split("=")[-1]
                parts = byte_range.split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
                if end >= file_size:
                    end = file_size - 1
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(SAMPLE_VIDEO_PATH, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
            else:
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(SAMPLE_VIDEO_PATH, "rb") as f:
                    self.wfile.write(f.read())
            return

        self.send_error(404, "Not Found")

def run(port=PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DemoRequestHandler)
    print(f"[*] Silicon Verdict Demo Server listening at http://localhost:{port}/")
    print(f"[*] Serving preview video from: {SAMPLE_VIDEO_PATH}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping Demo Server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
