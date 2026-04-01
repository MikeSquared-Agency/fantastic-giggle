import tkinter as tk


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress-1>", self.hide, add="+")

    def show(self, _event=None):
        if self.tip_window is not None:
            return

        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() - 34
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.overrideredirect(True)
        self.tip_window.wm_attributes("-topmost", True)
        self.tip_window.configure(bg="#11111b")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            bg="#11111b",
            fg="#cdd6f4",
            font=("Segoe UI", 9),
            padx=8,
            pady=4,
        )
        label.pack()
        self.tip_window.geometry(f"+{x}+{y}")

    def hide(self, _event=None):
        if self.tip_window is None:
            return
        try:
            self.tip_window.destroy()
        finally:
            self.tip_window = None


class VoiceBar:
    BAR_W, BAR_H = 620, 52
    BG = "#1e1e2e"
    BG_LIGHT = "#313244"
    FG = "#cdd6f4"
    FG_DIM = "#6c7086"
    BLUE = "#89b4fa"
    GREEN = "#a6e3a1"
    YELLOW = "#f9e2af"
    MAUVE = "#cba6f7"
    RED = "#f38ba8"
    FONT = ("Segoe UI", 13)

    MODE_META = {
        "draft_drop": {
            "icon": "🎙️",
            "name": "Draft & Drop",
            "key": "D",
            "color": BLUE,
        },
        "polish_prose": {
            "icon": "✨",
            "name": "Polish Prose",
            "key": "P",
            "color": MAUVE,
        },
        "command_control": {
            "icon": "⚡",
            "name": "Command & Control",
            "key": "C",
            "color": YELLOW,
        },
    }

    def __init__(self, on_close, master=None):
        self.on_close = on_close
        self.mode = "draft_drop"
        self.root = tk.Toplevel(master) if master is not None else tk.Tk()
        self._mode_buttons: dict[str, tk.Label] = {}
        self._build()
        self._position()

    def _build(self):
        r = self.root
        r.overrideredirect(True)
        r.wm_attributes("-topmost", True)
        r.wm_attributes("-alpha", 0.95)
        r.configure(bg=self.BG)
        r.resizable(False, False)
        r.bind("<Escape>", lambda _event: self.close())
        r.bind("<ButtonPress-1>", self._drag_start)
        r.bind("<B1-Motion>", self._drag_motion)
        r.bind("<KeyPress-d>", lambda _event: self.set_mode("draft_drop"))
        r.bind("<KeyPress-D>", lambda _event: self.set_mode("draft_drop"))
        r.bind("<KeyPress-p>", lambda _event: self.set_mode("polish_prose"))
        r.bind("<KeyPress-P>", lambda _event: self.set_mode("polish_prose"))
        r.bind("<KeyPress-c>", lambda _event: self.set_mode("command_control"))
        r.bind("<KeyPress-C>", lambda _event: self.set_mode("command_control"))

        for mode_name in ("draft_drop", "polish_prose", "command_control"):
            meta = self.MODE_META[mode_name]
            button = tk.Label(
                r,
                text=meta["icon"],
                bg=self.BG,
                fg=self.FG_DIM,
                font=("Segoe UI Emoji", 14),
                width=2,
                padx=4,
                cursor="hand2",
            )
            button.pack(side=tk.LEFT, padx=(10 if not self._mode_buttons else 4, 0))
            button.bind("<Button-1>", lambda _event, target=mode_name: self.set_mode(target))
            ToolTip(button, f'{meta["name"]} ({meta["key"]})')
            self._mode_buttons[mode_name] = button

        sep = tk.Frame(r, bg="#45475a", width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 12), pady=8)

        self.label = tk.Label(
            r,
            text="Listening (Draft & Drop)...",
            bg=self.BG,
            fg=self.FG,
            font=self.FONT,
            anchor="w",
            wraplength=410,
        )
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        close_button = tk.Label(
            r,
            text="✕",
            bg=self.BG,
            fg=self.FG_DIM,
            font=("Segoe UI", 12),
            cursor="hand2",
        )
        close_button.pack(side=tk.RIGHT, padx=14)
        close_button.bind("<Button-1>", lambda _event: self.close())
        close_button.bind("<Enter>", lambda _event: close_button.configure(fg=self.RED))
        close_button.bind("<Leave>", lambda _event: close_button.configure(fg=self.FG_DIM))

        self._sync_mode_buttons()

    def _position(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.BAR_W) // 2
        y = sh - self.BAR_H - 60
        self.root.geometry(f"{self.BAR_W}x{self.BAR_H}+{x}+{y}")

    def _drag_start(self, event):
        self._dx, self._dy = event.x, event.y

    def _drag_motion(self, event):
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _safe_after(self, callback):
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def _sync_mode_buttons(self):
        for mode_name, button in self._mode_buttons.items():
            meta = self.MODE_META[mode_name]
            is_active = mode_name == self.mode
            button.configure(
                bg=self.BG_LIGHT if is_active else self.BG,
                fg=meta["color"] if is_active else self.FG_DIM,
            )

    def set_mode(self, mode: str):
        if mode not in self.MODE_META:
            return
        self.mode = mode
        self._safe_after(self._sync_mode_buttons)
        self.set_listening()
        return "break"

    def set_listening(self):
        text = f'Listening ({self.MODE_META[self.mode]["name"]})...'
        self._safe_after(lambda: self.label.configure(text=text, fg=self.FG))

    def set_transcribing(self, text: str):
        display = text[:60] + "..." if len(text) > 60 else text
        self._safe_after(lambda: self.label.configure(text=display, fg=self.FG))

    def set_typed(self, text: str):
        display = f'Typed: "{text[:46]}"' if len(text) > 46 else f'Typed: "{text}"'
        self._safe_after(lambda: self.label.configure(text=display, fg=self.GREEN))
        self._safe_after(lambda: self.root.after(1500, self.set_listening))

    def set_refined(self, text: str):
        display = f'Refined: "{text[:44]}"' if len(text) > 44 else f'Refined: "{text}"'
        self._safe_after(lambda: self.label.configure(text=display, fg=self.MAUVE))
        self._safe_after(lambda: self.root.after(1500, self.set_listening))

    def set_command(self, name: str, shortcut: str):
        self._safe_after(
            lambda: self.label.configure(
                text=f"Command: {name}  →  {shortcut.upper()}",
                fg=self.YELLOW,
            )
        )
        self._safe_after(lambda: self.root.after(1500, self.set_listening))

    def close(self):
        self.on_close()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        self.root.mainloop()
