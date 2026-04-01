"""
Run this once before distributing:
    python build.py

What it does:
1. Downloads faster-whisper tiny.en model into models/whisper/tiny.en/
2. Runs PyInstaller to produce a single .exe with all models bundled
"""

import subprocess
import sys
from pathlib import Path
from faster_whisper import WhisperModel

ROOT       = Path(__file__).parent
WHISPER_DIR = ROOT / "models" / "whisper" / "tiny.en"
GEMMA_DIR   = ROOT / "models" / "functiongemma-270m-it"

def download_whisper():
    if WHISPER_DIR.exists() and any(WHISPER_DIR.iterdir()):
        print("Whisper tiny.en already present, skipping download.")
        return
    print("Downloading faster-whisper tiny.en...")
    WHISPER_DIR.mkdir(parents=True, exist_ok=True)
    # Trigger download by loading the model — faster-whisper caches to the path we give it
    WhisperModel("tiny.en", device="cpu", compute_type="int8",
                 download_root=str(ROOT / "models" / "whisper"))
    print("Whisper model ready.")

def build_exe():
    if not GEMMA_DIR.exists():
        print(f"ERROR: FunctionGemma model not found at {GEMMA_DIR}")
        print("Copy your model folder to models/functiongemma-270m-it/ and retry.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "VoiceDispatch",
        "--icon", "assets/icon.ico",
        # Bundle both model folders
        "--add-data", f"{GEMMA_DIR};models/functiongemma-270m-it",
        "--add-data", f"{WHISPER_DIR};models/whisper/tiny.en",
        # Hidden imports PyInstaller misses
        "--hidden-import", "transformers",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "sounddevice",
        "--hidden-import", "webrtcvad",
        "--hidden-import", "keyboard",
        "--hidden-import", "win32gui",
        "--hidden-import", "win32process",
        "--hidden-import", "pyperclip",
        "--hidden-import", "tkinter",
        "main.py"
    ]
    print("Building .exe...")
    subprocess.run(cmd, check=True)
    print("\nDone. Distributable: dist/VoiceDispatch.exe")

if __name__ == "__main__":
    download_whisper()
    build_exe()
