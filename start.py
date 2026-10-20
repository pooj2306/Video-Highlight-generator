"""
Universal launcher for Video Highlight Generator.
Run this from VS Code or any terminal:
    python start.py
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    print("=" * 60)
    print("       AI Video Highlight Generator - Web Server")
    print("=" * 60)

    venv_py = ROOT / "venv" / "Scripts" / "python.exe"
    py_bin = str(venv_py) if venv_py.exists() else sys.executable
    print(f"[OK] Python executable: {py_bin}")
    print("[OK] Starting server at http://127.0.0.1:8000 ...")

    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open("http://127.0.0.1:8000")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        subprocess.run(
            [py_bin, "-m", "uvicorn", "app.server:app", "--host", "127.0.0.1", "--port", "8000", "--reload", "--reload-dir", "app", "--reload-dir", "src"],
            cwd=str(ROOT),
            check=True
        )
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
    except Exception as e:
        print(f"\n[ERROR] Server exited with error: {e}")

if __name__ == "__main__":
    main()
