from transformers import AutoProcessor, AutoModelForCausalLM

processor = AutoProcessor.from_pretrained("google/functiongemma-270m-it")
model = AutoModelForCausalLM.from_pretrained("google/functiongemma-270m-it")

# --- each shortcut gets its own uniquely-named function ---
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

# Build schemas: one function per shortcut, no parameters needed
schemas = []
for func_name, (shortcut, desc) in SHORTCUT_DEFS.items():
    schemas.append({
        "type": "function",
        "function": {
            "name": func_name,
            "description": desc,
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    })

# Reverse lookup: function name -> shortcut
FUNC_TO_SHORTCUT = {name: sc for name, (sc, _) in SHORTCUT_DEFS.items()}

# --- parser ---
def parse_response(response: str) -> str | None:
    if "<start_function_call>" not in response:
        return None
    first_call = response.split("<start_function_call>")[1].split("<end_function_call>")[0]
    for func_name, shortcut in FUNC_TO_SHORTCUT.items():
        if func_name in first_call:
            return shortcut
    return None

# --- resolver ---
def resolve(transcript: str, schemas: list) -> str | None:
    messages = [
        {
            "role": "developer",
            "content": (
                "You are a voice command dispatcher for a Windows desktop tool. "
                "Call a function ONLY when the user explicitly intends to trigger a computer action or keyboard shortcut. "
                "Do NOT call any function for ordinary sentences, phrases, questions, or dictation. "
                "When in doubt, do not call a function."
            )
        },
        {"role": "user", "content": transcript}
    ]
    inputs = processor.apply_chat_template(
        messages,
        tools=schemas,
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
    print(f"  [raw] {transcript!r} -> {response!r}")
    return parse_response(response)

# --- test battery ---
test_cases = [
    # Clear commands
    ("save",                                  True,  "ctrl+s"),
    ("close tab",                             True,  "ctrl+w"),
    ("undo that",                             True,  "ctrl+z"),
    ("copy that",                             True,  "ctrl+c"),
    ("lock the computer",                     True,  "win+l"),
    ("mute",                                  True,  "volumemute"),
    ("take a screenshot",                     True,  "win+shift+s"),
    ("open file explorer",                    True,  "win+e"),
    ("reload the page",                       True,  "ctrl+r"),
    ("go back",                               True,  "alt+left"),

    # Noisy natural language
    ("oh can you just save this real quick",  True,  "ctrl+s"),
    ("get rid of this tab",                   True,  "ctrl+w"),
    ("oh no undo undo undo",                  True,  "ctrl+z"),
    ("can you lock my screen please",         True,  "win+l"),
    ("turn the volume up a bit",              True,  "volumeup"),
    ("go back to the previous page",          True,  "alt+left"),
    ("open a new tab",                        True,  "ctrl+t"),
    ("switch to another window",              True,  "alt+tab"),
    ("can you zoom in a little",              True,  "ctrl+plus"),
    ("bring back the tab I just closed",      True,  "ctrl+shift+t"),

    # Dictation — must return None
    ("the quick brown fox",                   False, None),
    ("I need to remember to call John",       False, None),
    ("so basically what I was thinking was",  False, None),
    ("this is a test of the system",          False, None),
    ("hey can you help me with something",    False, None),
]

# --- run ---
passed = ambiguous = failed = 0
misses = []

for transcript, expect_call, expected_shortcut in test_cases:
    result = resolve(transcript, schemas)
    if expect_call:
        if result == expected_shortcut:
            print(f"✓  '{transcript}' → {result}")
            passed += 1
        elif result is not None:
            print(f"~  '{transcript}' → got {result}, expected {expected_shortcut}")
            ambiguous += 1
            misses.append(f"  ~ '{transcript}' → got {result}, expected {expected_shortcut}")
        else:
            print(f"✗  '{transcript}' → None (expected {expected_shortcut})")
            failed += 1
            misses.append(f"  ✗ '{transcript}' → None (expected {expected_shortcut})")
    else:
        if result is None:
            print(f"✓  '{transcript}' → None (dictation, correct)")
            passed += 1
        else:
            print(f"✗  '{transcript}' → {result} (should have been dictation)")
            failed += 1
            misses.append(f"  ✗ '{transcript}' → {result} (should have been dictation)")

print(f"\n{passed} passed  {ambiguous} ambiguous  {failed} failed  / {len(test_cases)} total")
if misses:
    print("\nRemaining misses:")
    for m in misses:
        print(m)
