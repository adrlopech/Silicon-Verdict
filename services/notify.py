"""Tells the operator that something happened: a macOS notification (osascript) and, when NOTIFY_WEBHOOK is set, a JSON POST ({"text": ...}, which Slack, Discord-compatible
and ntfy-style endpoints accept). Never raises: a notification that cannot be sent must not stop a batch."""
import logging
import os
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def notify(title: str, message: str, webhook: Optional[str] = None) -> None:
    if sys.platform == "darwin":
        try:
            esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')  # noqa: E731
            subprocess.run(["osascript", "-e", f'display notification "{esc(message)}" with title "{esc(title)}"'], capture_output=True, timeout=10)
        except Exception as exc:  # noqa: BLE001
            logger.warning("desktop notification failed: %s", exc)
    url = webhook or os.environ.get("NOTIFY_WEBHOOK")
    if url:
        try:
            import requests
            requests.post(url, json={"text": f"{title}: {message}", "content": f"{title}: {message}"}, timeout=10)
        except Exception as exc:  # noqa: BLE001
            logger.warning("webhook notification failed: %s", exc)
