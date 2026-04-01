import ctypes
import queue
import threading
import tkinter as tk
from ctypes import wintypes
from tkinter import messagebox

import keyboard as kb
import win32gui
import pyperclip
from config import TRIGGER_HOTKEY
from gui import VoiceBar
from resolver import resolve, SHORTCUT_DEFS
from executor import fire
from refiner import refine
import stt

bar: VoiceBar | None = None
last_hwnd: int = 0
bar_lock = threading.Lock()
bar_opening = False
ui_root: tk.Tk | None = None
hotkey_events: queue.SimpleQueue[tuple[str, str | None]] = queue.SimpleQueue()
WM_HOTKEY = 0x0312
HOTKEY_ID = 1
MODIFIER_FLAGS = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "shift": 0x0004,
    "win": 0x0008,
}
SPECIAL_KEYS = {
    "tab": 0x09,
    "enter": 0x0D,
    "esc": 0x1B,
    "space": 0x20,
}


def show_error(message: str):
    if ui_root is not None:
        messagebox.showerror("VoiceDispatch", message, parent=ui_root)
        return

    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    try:
        messagebox.showerror("VoiceDispatch", message, parent=root)
    finally:
        root.destroy()


def inject_text(text: str):
    try:
        kb.write(text, delay=0.02)
    except Exception:
        pyperclip.copy(text)
        kb.send("ctrl+v")


def command_name(shortcut: str) -> str:
    return next(
        (
            name
            for name, (defined_shortcut, _) in SHORTCUT_DEFS.items()
            if defined_shortcut == shortcut
        ),
        shortcut,
    )


def parse_hotkey(hotkey: str) -> tuple[int, int]:
    modifiers = 0
    key_code = None

    for part in (segment.strip().lower() for segment in hotkey.split("+")):
        if part in MODIFIER_FLAGS:
            modifiers |= MODIFIER_FLAGS[part]
            continue

        if len(part) == 1 and part.isascii():
            key_code = ord(part.upper())
            continue

        key_code = SPECIAL_KEYS.get(part)
        if key_code is None:
            raise ValueError(f"Unsupported hotkey part: {part}")

    if key_code is None:
        raise ValueError(f"No primary key found in hotkey: {hotkey}")

    return modifiers, key_code


def on_utterance(transcript: str):
    global last_hwnd
    transcript = transcript.strip()
    active_bar = bar
    if not transcript or active_bar is None:
        return

    mode = active_bar.mode
    active_bar.set_transcribing(transcript)

    result = resolve(transcript) if mode == "command_control" else None

    try:
        if last_hwnd:
            win32gui.SetForegroundWindow(last_hwnd)
    except Exception:
        pass

    active_bar = bar
    if active_bar is None:
        return

    if mode == "draft_drop":
        inject_text(transcript)
        active_bar.set_typed(transcript)
    elif mode == "polish_prose":
        polished = refine(transcript)
        inject_text(polished)
        active_bar.set_refined(polished)
    else:  # command_control
        if result:
            fire(result)
            active_bar.set_command(command_name(result), result)
        else:
            inject_text(transcript)
            active_bar.set_typed(transcript)


def start_stt(local_bar: VoiceBar):
    try:
        stt.start(on_utterance)
        local_bar.set_listening()
    except Exception as exc:
        stt.stop()
        with bar_lock:
            global bar, bar_opening
            if bar is local_bar:
                bar = None
            bar_opening = False
        try:
            local_bar.root.after(0, local_bar.root.destroy)
        except Exception:
            pass
        if ui_root is not None:
            ui_root.after(0, lambda: show_error(f"Unable to start voice input.\n\n{exc}"))


def open_bar():
    global bar, last_hwnd, bar_opening

    with bar_lock:
        if bar is not None or bar_opening:
            return
        bar_opening = True

    last_hwnd = win32gui.GetForegroundWindow()
    local_bar = VoiceBar(on_close=close_bar, master=ui_root)
    local_bar.root.deiconify()
    local_bar.root.lift()
    local_bar.root.update()
    try:
        local_bar.root.focus_force()
        local_bar.root.after(10, local_bar.root.focus_force)
    except Exception:
        pass

    with bar_lock:
        bar = local_bar

    local_bar.set_transcribing("Starting microphone...")
    threading.Thread(target=start_stt, args=(local_bar,), daemon=True).start()


def close_bar():
    global bar, bar_opening
    stt.stop()
    with bar_lock:
        bar = None
        bar_opening = False


def hotkey_listener():
    try:
        modifiers, key_code = parse_hotkey(TRIGGER_HOTKEY)
    except ValueError as exc:
        hotkey_events.put(("error", str(exc)))
        return

    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, key_code):
        hotkey_events.put(("error", f"Unable to register hotkey: {TRIGGER_HOTKEY}"))
        return

    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                hotkey_events.put(("open", None))
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)


def pump_hotkey_events():
    while True:
        try:
            event_name, payload = hotkey_events.get_nowait()
        except queue.Empty:
            break

        if event_name == "open":
            open_bar()
        elif event_name == "error" and payload:
            show_error(payload)

    if ui_root is not None:
        ui_root.after(50, pump_hotkey_events)


def main():
    global ui_root

    if not stt.has_input_device():
        show_error("No audio input device was found.\n\nConnect a microphone and relaunch VoiceDispatch.")
        return

    ui_root = tk.Tk()
    ui_root.overrideredirect(True)
    ui_root.geometry("1x1+0+0")
    ui_root.wm_attributes("-alpha", 0.0)
    ui_root.wm_attributes("-topmost", True)
    print(f"VoiceDispatch ready — {TRIGGER_HOTKEY} to open")
    threading.Thread(target=hotkey_listener, daemon=True).start()
    ui_root.after(50, pump_hotkey_events)
    try:
        ui_root.mainloop()
    finally:
        stt.stop()


if __name__ == "__main__":
    main()
