import threading
import keyboard as kb
import win32gui
import pyperclip
from config import TRIGGER_HOTKEY
from gui import VoiceBar
from resolver import resolve, FUNC_TO_SHORTCUT
from executor import fire
import stt

bar: VoiceBar | None = None
last_hwnd: int = 0


def inject_text(text: str):
    try:
        kb.write(text, delay=0.02)
    except Exception:
        pyperclip.copy(text)
        kb.send("ctrl+v")


def on_utterance(transcript: str):
    global last_hwnd
    transcript = transcript.strip()
    if not transcript or bar is None:
        return

    bar.set_transcribing(transcript)

    result = resolve(transcript)

    win32gui.SetForegroundWindow(last_hwnd)

    if result:
        fire(result)
        # Find human-readable name for the bar
        name = next((n for n, (sc, _) in __import__("resolver").SHORTCUT_DEFS.items()
                     if sc == result), result)
        bar.set_command(name, result)
    else:
        inject_text(transcript)
        bar.set_typed(transcript)


def open_bar():
    global bar, last_hwnd
    if bar is not None:
        return

    last_hwnd = win32gui.GetForegroundWindow()
    bar = VoiceBar(on_close=close_bar)
    stt.start(on_utterance)
    bar.set_listening()

    threading.Thread(target=bar.run, daemon=True).start()


def close_bar():
    global bar
    stt.stop()
    bar = None


def main():
    kb.add_hotkey(TRIGGER_HOTKEY, open_bar)
    print(f"VoiceDispatch ready — {TRIGGER_HOTKEY} to open")
    kb.wait()


if __name__ == "__main__":
    main()
