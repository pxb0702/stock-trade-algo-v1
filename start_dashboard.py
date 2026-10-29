"""
One-Click Launcher for Stock Trade Algo v1 Interactive Dashboard
Usage:
    python start_dashboard.py
"""

import os
import sys

# Configure UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import webbrowser
import threading
import time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from web.app import app

def open_browser(port: int):
    time.sleep(1.2)
    url = f"http://127.0.0.1:{port}"
    print(f"[Dashboard] Opening web browser at {url} ...")
    webbrowser.open(url)

if __name__ == "__main__":
    PORT = 5000
    print("=" * 65)
    print("🚀 Starting Stock Trade Algo v1 Web Dashboard...")
    print(f"📊 Access URL: http://127.0.0.1:{PORT}")
    print("=" * 65)

    # Launch browser automatically
    threading.Thread(target=open_browser, args=(PORT,), daemon=True).start()

    # Start Flask Server
    app.run(host="0.0.0.0", port=PORT, debug=False)
