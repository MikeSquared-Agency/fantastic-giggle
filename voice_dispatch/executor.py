import keyboard

MODIFIER_MAP = {
    "ctrl": "ctrl", "alt": "alt", "shift": "shift",
    "win": "windows", "plus": "=", "minus": "-",
    "period": ".", "comma": ",", "slash": "/",
    "backtick": "`", "backslash": "\\"
}

def fire(shortcut: str):
    parts = [MODIFIER_MAP.get(p.strip(), p.strip()) for p in shortcut.lower().split("+")]
    keyboard.send("+".join(parts))
