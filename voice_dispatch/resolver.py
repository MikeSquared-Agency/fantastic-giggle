from transformers import AutoProcessor, AutoModelForCausalLM
from config import FUNCTIONGEMMA_DIR

# Load once at startup
processor = AutoProcessor.from_pretrained(FUNCTIONGEMMA_DIR, local_files_only=True)
model     = AutoModelForCausalLM.from_pretrained(FUNCTIONGEMMA_DIR, local_files_only=True)

SHORTCUT_DEFS = {
    "save_file":          ("ctrl+s",         "Save the current file or document"),
    "close_tab":          ("ctrl+w",         "Close the current browser tab"),
    "undo":               ("ctrl+z",         "Undo the last action"),
    "redo":               ("ctrl+y",         "Redo the last undone action"),
    "copy":               ("ctrl+c",         "Copy selected text or item to clipboard"),
    "cut":                ("ctrl+x",         "Cut selected text or item to clipboard"),
    "paste":              ("ctrl+v",         "Paste from clipboard"),
    "select_all":         ("ctrl+a",         "Select all content on the page"),
    "find":               ("ctrl+f",         "Open the find or search dialog"),
    "bold":               ("ctrl+b",         "Toggle bold text formatting"),
    "new_tab":            ("ctrl+t",         "Open a new browser tab"),
    "open_tab":           ("ctrl+t",         "Open a new tab in the browser"),
    "restore_tab":        ("ctrl+shift+t",   "Reopen the most recently removed browser tab"),
    "new_window":         ("ctrl+n",         "Open a new window"),
    "close_window":       ("alt+f4",         "Close the current window or application"),
    "switch_window":      ("alt+tab",        "Switch to another open window"),
    "lock_computer":      ("win+l",          "Lock the computer screen"),
    "show_desktop":       ("win+d",          "Minimize all windows and show the desktop"),
    "open_settings":      ("win+i",          "Open Windows settings"),
    "open_file_explorer": ("win+e",          "Open the file explorer"),
    "take_screenshot":    ("win+shift+s",    "Take a screenshot of a screen region"),
    "volume_up":          ("volumeup",       "Increase the system volume"),
    "volume_down":        ("volumedown",     "Decrease the system volume"),
    "mute_audio":         ("volumemute",     "Mute or unmute system audio"),
    "zoom_in":            ("ctrl+plus",      "Zoom in to make content larger"),
    "zoom_out":           ("ctrl+minus",     "Zoom out to make content smaller"),
    "default_zoom":       ("ctrl+0",         "Reset zoom level to 100 percent"),
    "navigate_back":      ("alt+left",       "Go back to the previously visited page in browser history"),
    "navigate_forward":   ("alt+right",      "Go forward to the next page in browser history after going back"),
    "reload_page":        ("ctrl+r",         "Reload or refresh the current page"),
    "open_task_manager":  ("ctrl+shift+esc", "Open the task manager"),
    "open_terminal":      ("win+x",          "Open a terminal or power user menu"),
}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": func_name,
            "description": desc,
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
    for func_name, (_, desc) in SHORTCUT_DEFS.items()
]

FUNC_TO_SHORTCUT = {name: sc for name, (sc, _) in SHORTCUT_DEFS.items()}

SYSTEM_PROMPT = (
    "You are a voice command dispatcher for a Windows desktop tool. "
    "Call a function ONLY when the user explicitly intends to trigger a computer action or keyboard shortcut. "
    "Do NOT call any function for ordinary sentences, phrases, questions, or dictation. "
    "When in doubt, do not call a function."
)

POLISH_SYSTEM_PROMPT = (
    "Clean up the following spoken transcript. "
    "Strip filler words such as um, uh, like, you know, basically, sort of, kind of, I mean. "
    "Fix capitalisation and add appropriate punctuation. "
    "Return only the cleaned text, nothing else."
)


def parse_response(response: str) -> str | None:
    if "<start_function_call>" not in response:
        return None
    first_call = response.split("<start_function_call>")[1].split("<end_function_call>")[0]
    for func_name, shortcut in FUNC_TO_SHORTCUT.items():
        if func_name in first_call:
            return shortcut
    return None


def polish(transcript: str) -> str:
    """Run the transcript through FunctionGemma for prose cleanup.

    Falls back to the rule-based refiner if the model call fails.
    """
    messages = [
        {"role": "developer", "content": POLISH_SYSTEM_PROMPT},
        {"role": "user",      "content": transcript},
    ]
    try:
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        outputs = model.generate(
            **inputs,
            pad_token_id=processor.eos_token_id,
            max_new_tokens=128,
        )
        result = processor.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True,
        ).strip()
        return result if result else transcript
    except Exception:
        from refiner import refine
        return refine(transcript)


def resolve(transcript: str) -> str | None:
    messages = [
        {"role": "developer", "content": SYSTEM_PROMPT},
        {"role": "user",      "content": transcript}
    ]
    try:
        inputs = processor.apply_chat_template(
            messages,
            tools=SCHEMAS,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        ).to(model.device)
        outputs = model.generate(
            **inputs,
            pad_token_id=processor.eos_token_id,
            max_new_tokens=64
        )
        response = processor.decode(
            outputs[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True
        )
        return parse_response(response)
    except Exception:
        return None
