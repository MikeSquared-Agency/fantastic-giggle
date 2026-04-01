import tkinter as tk

class VoiceBar:
    BAR_W, BAR_H = 620, 52
    BG     = "#1e1e2e"
    FG     = "#cdd6f4"
    ACCENT = "#89b4fa"
    GREEN  = "#a6e3a1"
    YELLOW = "#f9e2af"
    RED    = "#f38ba8"
    FONT   = ("Segoe UI", 13)

    def __init__(self, on_close, master=None):
        self.on_close = on_close
        self.root     = tk.Toplevel(master) if master is not None else tk.Tk()
        self._build()
        self._position()

    def _build(self):
        r = self.root
        r.overrideredirect(True)
        r.wm_attributes("-topmost", True)
        r.wm_attributes("-alpha", 0.95)
        r.configure(bg=self.BG)
        r.resizable(False, False)
        r.bind("<Escape>", lambda e: self.close())
        r.bind("<ButtonPress-1>", self._drag_start)
        r.bind("<B1-Motion>",     self._drag_motion)

        self.icon = tk.Label(r, text="\U0001f399", bg=self.BG, fg=self.ACCENT, font=("Segoe UI", 16))
        self.icon.pack(side=tk.LEFT, padx=(14, 6))

        self.label = tk.Label(r, text="Listening...", bg=self.BG, fg=self.FG,
                              font=self.FONT, anchor="w", width=44, wraplength=480)
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn = tk.Label(r, text="\u2715", bg=self.BG, fg="#6c7086", font=("Segoe UI", 12), cursor="hand2")
        btn.pack(side=tk.RIGHT, padx=14)
        btn.bind("<Button-1>", lambda e: self.close())
        btn.bind("<Enter>",    lambda e: btn.configure(fg=self.RED))
        btn.bind("<Leave>",    lambda e: btn.configure(fg="#6c7086"))

    def _position(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - self.BAR_W) // 2
        y  = sh - self.BAR_H - 60
        self.root.geometry(f"{self.BAR_W}x{self.BAR_H}+{x}+{y}")

    def _drag_start(self, e): self._dx, self._dy = e.x, e.y
    def _drag_motion(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    # -- state setters (thread-safe via root.after) --

    def _safe_after(self, callback):
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def set_listening(self):
        self._safe_after(lambda: [
            self.icon.configure(text="\U0001f399", fg=self.ACCENT),
            self.label.configure(text="Listening...", fg=self.FG)
        ])

    def set_transcribing(self, text: str):
        display = text[:60] + "..." if len(text) > 60 else text
        self._safe_after(lambda: [
            self.icon.configure(text="\u231b", fg=self.FG),
            self.label.configure(text=display, fg=self.FG)
        ])

    def set_typed(self, text: str):
        display = f'Typed: "{text[:46]}"' if len(text) > 46 else f'Typed: "{text}"'
        self._safe_after(lambda: [
            self.icon.configure(text="\u2713", fg=self.GREEN),
            self.label.configure(text=display, fg=self.GREEN)
        ])
        self._safe_after(lambda: self.root.after(1500, self.set_listening))

    def set_command(self, name: str, shortcut: str):
        self._safe_after(lambda: [
            self.icon.configure(text="\u26a1", fg=self.YELLOW),
            self.label.configure(text=f"Command: {name}  \u2192  {shortcut.upper()}", fg=self.YELLOW)
        ])
        self._safe_after(lambda: self.root.after(1500, self.set_listening))

    def close(self):
        self.on_close()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        self.root.mainloop()
