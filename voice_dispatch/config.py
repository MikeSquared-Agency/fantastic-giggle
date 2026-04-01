import sys
from pathlib import Path

# When frozen by PyInstaller, _MEIPASS is the temp extraction dir
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

FUNCTIONGEMMA_DIR = str(BASE_DIR / "models" / "functiongemma-270m-it")
WHISPER_DIR       = str(BASE_DIR / "models" / "whisper" / "tiny.en")

TRIGGER_HOTKEY    = "win+shift+d"
SAMPLE_RATE       = 16000
SILENCE_FRAMES    = 20       # ~600ms silence = utterance end
VAD_AGGRESSIVENESS = 2
FRAME_MS          = 30
