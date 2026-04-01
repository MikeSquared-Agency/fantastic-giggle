import sys
from pathlib import Path

# When frozen by PyInstaller, _MEIPASS is the temp extraction dir
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

def _resolve_model_dir(model_dir: Path) -> Path:
    if (model_dir / "config.json").exists():
        return model_dir

    nested_dir = model_dir / model_dir.name
    if (nested_dir / "config.json").exists():
        return nested_dir

    return model_dir


FUNCTIONGEMMA_DIR = str(_resolve_model_dir(BASE_DIR / "models" / "functiongemma-270m-it"))
WHISPER_DIR       = str(BASE_DIR / "models" / "whisper" / "tiny.en")
ICON_PATH         = str(BASE_DIR / "assets" / "icon.ico")

TRIGGER_HOTKEY    = "win+shift+d"
SAMPLE_RATE       = 16000
SILENCE_FRAMES    = 20       # ~600ms silence = utterance end
VAD_AGGRESSIVENESS = 2
FRAME_MS          = 30
